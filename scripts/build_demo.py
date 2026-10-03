import sys, time, json
sys.path.insert(0, "scripts")
from unity_mcp import MCP

m = MCP(timeout=1800)

print("--- refresh & compile ---")
print(m.text("refresh_unity", {"mode": "force", "scope": "scripts", "compile": "request", "wait_for_ready": True})[:300])
time.sleep(4)
print("errors:", m.text("read_console", {"action": "get", "types": ["error"], "count": 10, "format": "plain"})[:800])

print("--- build ---")
r = m.text("manage_build", {
    "action": "build",
    "target": "windows64",
    "output_path": "<PROJECT_ROOT>/DEMO成品/HKFlightDemo.exe",
    "scenes": '["Assets/_FlightDemo/Scenes/HKFlight_Demo.unity"]',
    "development": "false",
    "options": '["clean_build"]',
})
print(r[:4000])
