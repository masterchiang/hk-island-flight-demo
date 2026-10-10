import sys, time
sys.path.insert(0, "scripts")
from unity_mcp import MCP

m = MCP(timeout=300)
print("play ->", m.text("manage_editor", {"action": "play"})[:150])
time.sleep(3)

PROBE = r'''
var t=System.Type.GetType("HKFlightDemo.DemoHUD, Assembly-CSharp");
var hud=UnityEngine.Object.FindFirstObjectByType(t);
if(hud==null) return "WAIT";
if(((UnityEngine.Component)hud).transform.Find("FlightDemo_HUD_Canvas")==null) return "WAIT";
return "READY";
'''
r = ""
for _ in range(40):
    r = m.text("execute_code", {"action": "execute", "code": PROBE})
    if "READY" in r:
        break
    time.sleep(1.0)
print("probe:", r.strip()[:60])

TEST = r'''
var t=System.Type.GetType("HKFlightDemo.DemoHUD, Assembly-CSharp");
var hud=UnityEngine.Object.FindFirstObjectByType(t);
var ft=System.Type.GetType("HKFlightDemo.FlightController, Assembly-CSharp");
var fc=UnityEngine.Object.FindFirstObjectByType(ft);
var c=(UnityEngine.Component)hud;
var canvas=c.transform.Find("FlightDemo_HUD_Canvas");
var bot=canvas.Find("BottomBar");
var bgm=c.transform.Find("FlightDemo_BGM").GetComponent<UnityEngine.AudioSource>();
var sb=new System.Text.StringBuilder();
int fail=0;
System.Action<string,bool> chk = (name, ok) => { sb.AppendLine((ok?"PASS  ":"FAIL  ") + name); if(!ok) fail++; };
System.Action<string> click = (btn) => { bot.Find(btn).GetComponent<UnityEngine.UI.Button>().onClick.Invoke(); };
System.Func<string,string> label = (btn) => bot.Find(btn).GetComponentInChildren<UnityEngine.UI.Text>().text;

click("MusicButton");
chk("音乐按钮 #1 -> 停止 & 文案=开启背景音乐", (!bgm.isPlaying) && label("MusicButton")=="开启背景音乐");
click("MusicButton");
chk("音乐按钮 #2 -> 播放 & 文案=关闭背景音乐", bgm.isPlaying && label("MusicButton")=="关闭背景音乐");

float t0=bgm.time; System.Threading.Thread.Sleep(120); 
sb.AppendLine("  音频时间在播放中前进: " + t0.ToString("F2") + " -> " + bgm.time.ToString("F2"));

click("UnlockButton");
chk("解锁驾驶 -> Manual", (bool)ft.GetProperty("Manual").GetValue(fc));
click("ResetButton");
chk("一键复位 -> 回到自动巡航且进度归零", (!(bool)ft.GetProperty("Manual").GetValue(fc)) && ((float)ft.GetProperty("Progress").GetValue(fc) < 0.001f));
click("PauseButton");
bool paused1=(bool)ft.GetProperty("Paused").GetValue(fc);
click("PauseButton");
bool paused2=(bool)ft.GetProperty("Paused").GetValue(fc);
chk("暂停按钮 -> 切换暂停/继续", paused1 && !paused2);
click("HelpButton");
bool help1=(bool)t.GetProperty("HelpVisible").GetValue(hud);
click("HelpButton");
bool help2=(bool)t.GetProperty("HelpVisible").GetValue(hud);
chk("帮助按钮 -> 打开/关闭", help1 && !help2);
click("ExitButton");
bool ex1=(bool)t.GetProperty("ExitVisible").GetValue(hud);
t.GetMethod("CloseExit").Invoke(hud,null);
bool ex2=(bool)t.GetProperty("ExitVisible").GetValue(hud);
chk("退出按钮 -> 打开确认框（不真正退出）", ex1 && !ex2);
chk("背景音乐未受暂停/复位影响", bgm.isPlaying && bgm.loop);
sb.AppendLine("---- 失败项: " + fail);
return sb.ToString();
'''
print("=== 按钮功能回归 ===")
print(m.text("execute_code", {"action": "execute", "code": TEST}))
print("errors:", m.text("read_console", {"action": "get", "types": ["error"], "count": 10})[:500])
print("stop ->", m.text("manage_editor", {"action": "stop"})[:150])
