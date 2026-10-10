import sys, time, re
sys.path.insert(0, "scripts")
from unity_mcp import MCP

m = MCP(timeout=600)

FINAL_TEX = r'''
if(UnityEngine.Application.isPlaying) return "ABORT: playmode";
string p="Assets/_FlightDemo/Resources/LOGO.jpg";
var ti=UnityEditor.AssetImporter.GetAtPath(p) as UnityEditor.TextureImporter;
ti.textureType=UnityEditor.TextureImporterType.Default;
ti.maxTextureSize=4096;
ti.mipmapEnabled=false;
ti.wrapMode=UnityEngine.TextureWrapMode.Clamp;
ti.sRGBTexture=true;
ti.alphaSource=UnityEditor.TextureImporterAlphaSource.None;
ti.npotScale=UnityEditor.TextureImporterNPOTScale.None;      // 保持宽高比，不做 POT 吸附
ti.textureCompression=UnityEditor.TextureImporterCompression.CompressedHQ;
ti.ClearPlatformTextureSettings("Standalone");
ti.SaveAndReimport();
var tex=UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Texture2D>(p);
return "final: " + tex.width + "x" + tex.height + " aspect=" + ((float)tex.width/tex.height).ToString("F4")
     + " | maxSize=" + ti.maxTextureSize + " compress=" + ti.textureCompression + " npot=" + ti.npotScale
     + " alpha=" + ti.alphaSource + " mip=" + ti.mipmapEnabled;
'''
print(m.text("execute_code", {"action": "execute", "code": FINAL_TEX}))
time.sleep(3)

print("--- play ---")
print(m.text("manage_editor", {"action": "play"})[:150])

PROBE = r'''
var t=System.Type.GetType("HKFlightDemo.DemoStartup, Assembly-CSharp");
var st=UnityEngine.Object.FindFirstObjectByType(t);
if(st==null) return "WAIT";
var c=(UnityEngine.Component)st;
var ft=System.Type.GetType("HKFlightDemo.FlightController, Assembly-CSharp");
var fc=UnityEngine.Object.FindFirstObjectByType(ft);
var canvas=c.transform.Find("FlightDemo_Logo_Canvas");
var sb=new System.Text.StringBuilder();
sb.Append("canvas=").Append(canvas!=null?"YES":"GONE");
if(canvas!=null){
  var raw=canvas.Find("Logo");
  sb.Append(" | logoChild=").Append(raw!=null?"YES":"NO");
  if(raw!=null){ var r=raw.GetComponent<UnityEngine.UI.RawImage>(); var rect=raw.GetComponent<UnityEngine.RectTransform>();
    sb.Append(" tex=").Append(r.texture==null?"null":(r.texture.width+"x"+r.texture.height));
    sb.Append(" rectW=").Append(rect.rect.width.ToString("F0")).Append(" rectH=").Append(rect.rect.height.ToString("F0"));
    sb.Append(" aspect=").Append((rect.rect.width/Mathf.Max(1f,rect.rect.height)).ToString("F3"));
  }
  sb.Append(" | sortingOrder=").Append(canvas.GetComponent<UnityEngine.Canvas>().sortingOrder);
}
if(fc!=null){ sb.Append(" | flightPaused=").Append(ft.GetProperty("Paused").GetValue(fc)); sb.Append(" progress=").Append(((float)ft.GetProperty("Progress").GetValue(fc))*100f).Append("%"); }
sb.Append(" | unscaledTime=").Append(UnityEngine.Time.unscaledTime.ToString("F2"));
return sb.ToString();
'''

firstSeen = None
t0 = time.time()
last = ""
while time.time() - t0 < 25:
    try:
        last = m.text("execute_code", {"action": "execute", "code": PROBE})
    except Exception as e:
        last = "ERR " + str(e)[:80]
    if "canvas=YES" in last or "canvas=GONE" in last:
        if firstSeen is None and "canvas=YES" in last:
            firstSeen = time.time()
            print("[%5.2fs] 首次看到 LOGO canvas: %s" % (time.time() - t0, last.strip()[-260:]))
            print("--- 截图：LOGO 展示中 ---")
            print(m.text("manage_camera", {"action": "screenshot", "screenshot_file_name": "startup_logo_splash.png"})[:150])
        if firstSeen is not None and "canvas=GONE" in last:
            print("[%5.2fs] LOGO canvas 已消失: %s" % (time.time() - t0, last.strip()[-260:]))
            break
    time.sleep(0.2)

print("LOGO 可见时长(含轮询误差): %.2f s" % (time.time() - firstSeen if firstSeen else -1))
print("--- 截图：进入 DEMO ---")
print(m.text("manage_camera", {"action": "screenshot", "screenshot_file_name": "startup_demo_after_logo.png"})[:150])
time.sleep(1.0)
print("最终:", m.text("execute_code", {"action": "execute", "code": PROBE}).strip()[-260:])
print("errors:", m.text("read_console", {"action": "get", "types": ["error"], "count": 8})[:400])
print("stop ->", m.text("manage_editor", {"action": "stop"})[:120])
