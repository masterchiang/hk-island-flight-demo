"""
Unity MCP (mcp-for-unity-server) Streamable-HTTP 极简客户端。
用于在 WorkBuddy 会话里直接驱动 Unity 编辑器。

用法：
  from unity_mcp import MCP
  m = MCP()
  print(m.tools())
  print(m.call("manage_editor", {"action": "get_state"}))
"""
import json
import urllib.request
import urllib.error

URL = "http://127.0.0.1:8080/mcp"


class MCPError(RuntimeError):
    pass


class MCP:
    def __init__(self, url=URL, timeout=180):
        self.url = url
        self.timeout = timeout
        self.sid = None
        self.rid = 0
        self._init()

    # ---------- 低层 ----------
    def _post(self, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.sid:
            req.add_header("mcp-session-id", self.sid)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                if r.headers.get("mcp-session-id"):
                    self.sid = r.headers["mcp-session-id"]
                body = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise MCPError(f"HTTP {e.code}: {body[:500]}")
        return self._parse_sse(body)

    @staticmethod
    def _parse_sse(body):
        msgs = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    msgs.append(json.loads(line[5:].strip()))
                except json.JSONDecodeError:
                    pass
        if not msgs:
            try:
                msgs.append(json.loads(body))
            except json.JSONDecodeError:
                pass
        return msgs

    def _rpc(self, method, params=None, notify=False):
        self.rid += 1
        p = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            p["params"] = params
        if not notify:
            p["id"] = self.rid
        msgs = self._post(p)
        if notify:
            return None
        for m in msgs:
            if m.get("id") == p.get("id"):
                if "error" in m:
                    raise MCPError(json.dumps(m["error"], ensure_ascii=False))
                return m.get("result")
        return msgs

    def _init(self):
        self._rpc("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "workbuddy", "version": "1.0"}})
        self._rpc("notifications/initialized", {}, notify=True)

    # ---------- 高层 ----------
    def tools(self):
        r = self._rpc("tools/list", {})
        return r.get("tools", []) if isinstance(r, dict) else []

    def call(self, name, args=None, unity_instance=None):
        a = dict(args or {})
        if unity_instance:
            a["unity_instance"] = unity_instance
        r = self._rpc("tools/call", {"name": name, "arguments": a})
        return r

    def text(self, name, args=None, unity_instance=None):
        """把工具结果压成纯文本。"""
        r = self.call(name, args, unity_instance)
        if not isinstance(r, dict):
            return json.dumps(r, ensure_ascii=False)[:4000]
        out = []
        for c in r.get("content", []):
            if c.get("type") == "text":
                out.append(c.get("text", ""))
            else:
                out.append(json.dumps(c, ensure_ascii=False)[:2000])
        if r.get("isError"):
            out.insert(0, "[isError]")
        return "\n".join(out)

    def resource(self, uri):
        return self._rpc("resources/read", {"uri": uri})


if __name__ == "__main__":
    import sys
    m = MCP()
    mode = sys.argv[1] if len(sys.argv) > 1 else "tools"
    if mode == "tools":
        for t in m.tools():
            print(t["name"], "-", (t.get("description") or "").split("\n")[0][:110])
    elif mode == "resources":
        for r in m._rpc("resources/list", {}).get("resources", []):
            print(r["uri"], "|", r.get("name"))
    elif mode == "call":
        name = sys.argv[2]
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(m.text(name, args))
    elif mode == "read":
        print(json.dumps(m.resource(sys.argv[2]), ensure_ascii=False)[:6000])
