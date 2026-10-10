"""Play Mode 动态验证：加速跑完整圈，记录飞机位置轨迹与飞控计数器。"""
import json, sys, time
sys.path.insert(0, "scripts")
from unity_mcp import MCP, MCPError

ROOT = r"<PROJECT_ROOT>"
TRACK = ROOT + "/output/FlightDemo/playmode_track_v5.json"


def connect():
    for _ in range(20):
        try:
            return MCP(timeout=300)
        except Exception as e:
            print("  connect retry:", e)
            time.sleep(1.5)
    raise SystemExit("无法连接 Unity MCP")


m = connect()
print("play ->", m.text("manage_editor", {"action": "play"})[:200])
time.sleep(3)

# 等待 FlightController 就绪
probe = r'''
var t=System.Type.GetType("HKFlightDemo.FlightController, Assembly-CSharp");
if(t==null) return "NOTYPE";
var fc=UnityEngine.Object.FindFirstObjectByType(t);
if(fc==null) return "NOFC";
return "READY ready=" + t.GetProperty("Ready").GetValue(fc) + " paused=" + t.GetProperty("Paused").GetValue(fc);
'''
for i in range(40):
    try:
        r = m.text("execute_code", {"action": "execute", "code": probe})
    except Exception as e:
        print("  probe err", e); r = ""
    if "READY" in r:
        print("probe:", r.strip().replace("\\r", " ")); break
    time.sleep(1.0)

# 加速
m.text("execute_code", {"action": "execute", "code": "UnityEngine.Time.timeScale=8f; return UnityEngine.Time.timeScale.ToString();"})

sample = r'''
var t=System.Type.GetType("HKFlightDemo.FlightController, Assembly-CSharp");
var fc=UnityEngine.Object.FindFirstObjectByType(t);
var sb=new System.Text.StringBuilder();
sb.Append(((float)t.GetProperty("Progress").GetValue(fc)).ToString("F4"));
var p=(UnityEngine.Vector3)t.GetProperty("Position").GetValue(fc);
sb.Append("|" + p.x.ToString("F0") + "," + p.y.ToString("F0") + "," + p.z.ToString("F0"));
sb.Append("|" + ((float)t.GetProperty("Speed").GetValue(fc)).ToString("F1"));
sb.Append("|" + t.GetProperty("ResetCount").GetValue(fc));
sb.Append("|" + t.GetProperty("RejectedMoves").GetValue(fc));
sb.Append("|" + t.GetProperty("ProtectionCount").GetValue(fc));
sb.Append("|" + t.GetProperty("Protecting").GetValue(fc));
sb.Append("|" + t.GetProperty("Notice").GetValue(fc));
return sb.ToString();
'''

rows = []
t0 = time.time()
while time.time() - t0 < 45:
    try:
        r = m.text("execute_code", {"action": "execute", "code": sample})
        s = r.strip()
        if s.count("|") >= 7:
            parts = s.split("|")
            rows.append(parts)
    except Exception as e:
        print("  sample err:", str(e)[:120])
    time.sleep(0.35)
print("samples:", len(rows))

m.text("execute_code", {"action": "execute", "code": "UnityEngine.Time.timeScale=1f; return UnityEngine.Time.timeScale.ToString();"})
print("stop ->", m.text("manage_editor", {"action": "stop"})[:200])
time.sleep(2)

json.dump(rows, open(TRACK, "w"), ensure_ascii=False, indent=1)
print("saved", TRACK)
if rows:
    print("first:", rows[0])
    print("last :", rows[-1])
    prog = [float(r[0]) for r in rows]
    print("progress range:", min(prog), "->", max(prog), " laps covered:", len([1 for i in range(1, len(prog)) if prog[i] < prog[i-1]]))
    print("reset counts:", sorted(set(int(r[3]) for r in rows)))
    print("rejected   :", sorted(set(int(r[4]) for r in rows)))
    print("protection :", sorted(set(int(r[5]) for r in rows)))
    print("protecting :", sorted(set(r[6] for r in rows)))
