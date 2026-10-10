"""Build the Cessna demo using the currently connected Unity editor (stop Play Mode first)."""
import json, time
from pathlib import Path
from unity_mcp import MCP
ROOT=Path(__file__).resolve().parents[1]
m=MCP(timeout=1800)
print(m.text("refresh_unity", {"mode":"force","scope":"all","compile":"request","wait_for_ready":True}))
time.sleep(3)
args={"action":"build","target":"windows64","output_path":str(ROOT/"香港岛Cessna310环岛飞行DEMO/HKFlightDemo.exe"),"scenes":json.dumps(["Assets/_FlightDemo/Scenes/HKFlight_Demo.unity"]),"development":"false","options":json.dumps(["clean_build"])}
raw=m.text("manage_build",args);print(raw)
response=json.loads(raw)
job=response.get("data",{}).get("job_id")
if job:
 for _ in range(360):
  time.sleep(5)
  raw=m.text("manage_build",{"action":"status","job_id":job});response=json.loads(raw)
  state=response.get("data",{}).get("result")
  if state in ("succeeded","failed","cancelled"):
   print(raw)
   if state!="succeeded":raise RuntimeError(raw)
   break
 else:raise TimeoutError("Build status exceeded 30-minute bound; inspect Unity without re-submitting build.")
