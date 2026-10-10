using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace HKFlightDemo.Editor
{
    /// <summary>Bounded smoke checks for this one-off demo. The cases follow the live scene dimensions.</summary>
    public static class FlightDemoChecks
    {
        [Serializable] private sealed class Report
        {
            public string observedLocalTime;
            public string stage;
            public List<string> passed = new List<string>();
            public string limitations;
        }
        private static void Require(bool value,string message) { if(!value) throw new Exception("[HKFlight CHECK FAILED] "+message); }
        private static FlightController Flight()
        {
            Require(Application.isPlaying,"Enter Play Mode before running checks");
            var f=UnityEngine.Object.FindAnyObjectByType<FlightController>();
            Require(f!=null && f.Ready,"Flight is ready"); return f;
        }
        private static Report NewReport(string stage,string limitations)
        { return new Report { observedLocalTime=DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss zzz"),stage=stage,limitations=limitations }; }

        public static string CheckStep2()
        {
            var f=Flight();bool keyboard=f.readKeyboard;f.readKeyboard=false;
            var report=NewReport("Step 2 / current scene", "Three deterministic simulated laps; not three real-time laps. Mouse hand-feel requires manual inspection.");
            try
            {
                f.ResetFlight("自动航线检查中");int rejected=f.RejectedMoves;float last=f.Progress;int loops=0;
                int ticks=Mathf.CeilToInt(f.route.Length*3.01f/f.cruiseSpeed/.02f);
                Require(ticks<500000,"Route check is bounded");
                for(int i=0;i<ticks;i++)
                {
                    Vector3 previous=f.Position;f.Simulate(.02f);
                    Require(f.safety.SegmentSafe(previous,f.Position),"Whole route segment is safe");
                    float move=Vector3.Distance(previous,f.Position),nominal=f.cruiseSpeed*.02f;
                    Require(move>nominal*.85f && move<nominal*1.15f,"Route has no jump and approximately constant speed");
                    if(f.Progress<last)loops++;last=f.Progress;
                }
                Require(loops>=3 && f.RejectedMoves==rejected,"Three laps, no rejected move or safety reset");
                report.passed.Add("3 complete simulated laps on the configured route; continuous closure and full-envelope safety");
                var camera=UnityEngine.Object.FindAnyObjectByType<DemoOrbitCamera>();
                Require(camera!=null && camera.flight==f,"Orbit camera is wired");Vector3 p=f.Position;camera.Recenter();
                Require(f.Position==p,"Camera recenter does not steer aircraft");
                report.passed.Add("Camera recenter leaves flight state unchanged");
                return Save(report,"step2_real_models_checks.json");
            }
            finally { f.readKeyboard=keyboard; f.ResetFlight(); }
        }

        public static string CheckStep3()
        {
            var f=Flight();var s=f.safety;bool keyboard=f.readKeyboard;f.readKeyboard=false;
            var report=NewReport("Step 3 / current safety geometry", s.enforceShield?"Tests the configured conservative volume, not individual building collision physics. Resets are permitted emergency outcomes.":"Debug override: shield enforcement is intentionally disabled; sea, world boundary, numerical validity and manual-flight checks remain relevant.");;
            try
            {
                Vector3 center=s.transform.position;float pad=s.aircraftRadius+s.margin;
                float height=Mathf.Max(s.minimumSeaClearance+pad+60,Mathf.Min(s.shieldTop-80,350));
                float reach=s.shieldRadii.x+700;
                Require(s.HitsShield(center+new Vector3(-reach,height,0),center+new Vector3(reach,height,0),pad),"Continuous segment across whole shield");
                Require(s.HitsShield(center+Vector3.up*height,center+Vector3.up*height,pad),"Starting inside is detected");
                float above=s.shieldTop+pad+220;
                Require(!s.HitsShield(center+new Vector3(-reach,above,0),center+new Vector3(reach,above,0),pad),"Clear crossing above shield allowed");
                Require(s.HitsShield(center+Vector3.up*above,center+Vector3.up*height,pad),"Top entry is blocked");
                Require(!s.SegmentSafe(center+new Vector3(reach,90,0),center+new Vector3(reach,20,0)),"Sea clearance enforced");
                Require(!s.SegmentSafe(center+new Vector3(reach,height,0),center+new Vector3(s.worldHalfSize.x+100,height,0)),"World boundary enforced");
                Require(!s.SegmentSafe(new Vector3(float.NaN,1,0),Vector3.zero),"Non-finite position is rejected");
                report.passed.Add("Continuous shield crossing / initial overlap / top entry / safe overflight / sea / world / NaN cases");
                if(!s.enforceShield)
                {
                    report.passed.Add("Shield enforcement disabled by user debug mode; analytical shield geometry remains available for re-enable");
                    f.ResetFlight();f.Unlock();f.ManualInput=Vector2.right;Quaternion debugRotation=f.Rotation;f.Simulate(.25f);
                    Require(Quaternion.Angle(debugRotation,f.Rotation)>.1f && s.SegmentSafe(f.Position,f.Position),"Manual flight works with debug shield override");
                    report.passed.Add("Manual flight and 250 ms substeps work with shield override");
                    return Save(report,"step3_debug_mode_checks.json");
                }
                var scenarios=new[] {
                    center+new Vector3(s.shieldRadii.x+850,height,0),center+new Vector3(-s.shieldRadii.x-850,height,0),
                    center+new Vector3(0,height,s.shieldRadii.y+850),center+new Vector3(0,height,-s.shieldRadii.y-850),
                    center+new Vector3(0,s.shieldTop+350,0),center+new Vector3(reach,s.minimumSeaClearance+pad+95,0)
                };
                int protections=f.ProtectionCount,resets=0;bool sawProtection=false;float maxActiveYawDelta=0;;
                for(int n=0;n<scenarios.Length;n++)
                {
                    Require(s.SegmentSafe(scenarios[n],scenarios[n]),"Each approach begins in a genuinely safe position");
                    Vector3 direction=n>=4?new Vector3(.08f,-1,0):((center+Vector3.up*height)-scenarios[n]).normalized;
                    f.ResetFlight();f.SetTestPose(scenarios[n],Quaternion.LookRotation(direction),f.maximumSpeed);float initialYaw=f.Rotation.eulerAngles.y;;
                    f.ManualInput=Vector2.zero;f.ThrottleInput=0;
                    for(int i=0;i<700;i++)
                    {
                        Vector3 previous=f.Position;bool manual=f.Manual;f.Simulate(.02f);if(f.Protecting){sawProtection=true;maxActiveYawDelta=Mathf.Max(maxActiveYawDelta,Mathf.Abs(Mathf.DeltaAngle(initialYaw,f.Rotation.eulerAngles.y)));};
                        if(manual && !f.Manual)resets++;
                        else Require(s.SegmentSafe(previous,f.Position),"Every submitted non-reset segment is safe");
                        Require(s.SegmentSafe(f.Position,f.Position),"Final full-aircraft envelope remains safe");
                    }
                }
                Require(f.ProtectionCount>protections,"Prediction really engaged, rather than cases resetting from an unsafe start");
                report.passed.Add("6 valid maximum-speed approaches/dives; safe continuous motion or emergency reset; reset outcomes="+resets);Require(sawProtection,"Protection takeover engaged");Require(maxActiveYawDelta<0.01f,"Protection preserves heading while active; max yaw delta="+maxActiveYawDelta);report.passed.Add("Protection is climb-only while active; max active yaw delta="+maxActiveYawDelta.ToString("F3"));;
                f.ResetFlight();f.SetTestPose(center+new Vector3(s.worldHalfSize.x-pad-15,height,0),Quaternion.LookRotation(Vector3.right),f.maximumSpeed);
                for(int i=0;i<60;i++)f.Simulate(.02f);
                Require(!f.Manual && s.SegmentSafe(f.Position,f.Position),"Boundary returns to safe automatic mode");
                report.passed.Add("Horizontal edge reset returns to tour mode");
                f.ResetFlight();f.Unlock();f.ManualInput=Vector2.right;Quaternion rotation=f.Rotation;f.Simulate(.25f);
                Require(Quaternion.Angle(rotation,f.Rotation)>.1f && s.SegmentSafe(f.Position,f.Position),"Manual turn and long-delta substeps work");
                report.passed.Add("Manual turn and 250 ms substep safety");
                return Save(report,"step3_real_models_checks.json");
            }
            finally { f.readKeyboard=keyboard;f.ResetFlight(); }
        }

        private static string uiCheckStatus = "not_started";
        public static string GetStep4Status() { return uiCheckStatus; }
        public static string CheckStep4()
        {
            if (uiCheckStatus == "running") return uiCheckStatus;
            var f = Flight(); var hud = UnityEngine.Object.FindAnyObjectByType<DemoHUD>();
            Require(hud != null && hud.HudCanvas != null && hud.flight == f, "HUD exists and references flight");
            uiCheckStatus = "running";
            hud.StartCoroutine(CheckStep4AcrossFrames(f, hud));
            return "running - inspect GetStep4Status() and step4_ui_checks.json after the frame-spaced pointer checks";
        }
        private static System.Collections.IEnumerator CheckStep4AcrossFrames(FlightController f, DemoHUD hud)
        {
            bool keyboard = f.readKeyboard, hudKeyboard = hud.readKeyboard, focusPause = f.pauseOnFocusLoss;
            f.readKeyboard = false; hud.readKeyboard = false; f.pauseOnFocusLoss = false;
            var report = NewReport("Step 4 / UI and reset", "Real Button pointer handlers and GraphicRaycaster hits are tested after render frames. OS keyboard/mouse feel and Windows Player quit remain separate checks.");
            var steps = new List<Action> {
                () => { hud.ResetFlight(); hud.RefreshInterface(); },
                () => { Click(hud,"BottomBar/UnlockButton"); Require(f.Manual,"Unlock button activates manual flight"); },
                () => { Click(hud,"BottomBar/PauseButton"); Require(f.Paused,"Pause stops simulation"); Vector3 pos=f.Position; f.Simulate(.25f); Require(f.Position==pos,"No movement while paused"); },
                () => { Click(hud, hud.showPauseOverlay ? "PauseOverlay/Card/ResumeButton" : "BottomBar/PauseButton"); Require(!f.Paused && f.Manual,"Continue restores manual state"); },
                () => { Click(hud,"BottomBar/HelpButton"); Require(hud.HelpVisible && f.Paused,"Help pauses flight"); },
                () => { Click(hud,"HelpPanel/Card/CloseHelp"); Require(!hud.HelpVisible && !f.Paused,"Closing help restores running state"); },
                () => { hud.TogglePause(); hud.ToggleHelp(); },
                () => { hud.ToggleHelp(); Require(f.Paused,"Help opened while paused returns to paused"); hud.Resume(); },
                () => { Click(hud,"BottomBar/ExitButton"); Require(hud.ExitVisible && f.Paused,"Exit opens confirmation"); },
                () => { Click(hud,"ExitPanel/Card/Cancel"); Require(!hud.ExitVisible && !f.Paused,"Exit cancellation restores running state"); },
                () => { hud.TogglePause(); hud.OpenExit(); },
                () => { hud.CloseExit(); Require(f.Paused,"Exit cancellation preserves pre-existing pause"); hud.OpenExit(); },
                () => {
                    hud.ResetFlight(); Require(!hud.ExitVisible && !hud.HelpVisible && !f.Paused && !f.Manual,"Reset closes modals and restores tour");
                    for(int i=0;i<50;i++){hud.ResetFlight();Require(!f.Manual&&!f.Paused&&!f.Protecting,"Repeated reset is idempotent");}
                    Vector3 spawn,dir; f.route.Evaluate(0,out spawn,out dir);
                    Require(Vector3.Distance(f.Position,spawn)<.01f && Vector3.Distance(f.transform.position,spawn)<.01f,"Motor/display pose reset together");
                    Require(Mathf.Abs(f.Speed-f.cruiseSpeed)<.01f && f.Progress<.001f && f.ManualInput==Vector2.zero && f.ThrottleInput==0,"Reset clears progress, target speed and inputs");
                    var camera=UnityEngine.Object.FindAnyObjectByType<DemoOrbitCamera>();Require(camera!=null&&!camera.FreeLook,"Reset returns camera to follow");
                },
                () => {
                    Canvas.ForceUpdateCanvases(); VerifyVisibleRects(hud);
                    report.passed.Add("Rendered pointer/raycast unlock, pause, continue, help and exit cancellation; prior pause state preserved");
                    report.passed.Add("50 repeated resets; modal cleanup, motor/display pose, route progress, inputs and camera reset");
                    report.passed.Add("All primary HUD controls and title/mode rectangles inside Canvas");
                    uiCheckStatus=Save(report,"step4_ui_checks.json");
                }
            };
            try
            {
                foreach(var step in steps)
                {
                    // Newly enabled graphics get their raycast depth after the normal Canvas render pass.
                    yield return null; yield return null;
                    bool failed=false;
                    try { step(); }
                    catch(Exception ex) { uiCheckStatus="FAILED: "+ex.Message; Debug.LogError(uiCheckStatus); failed=true; }
                    if(failed) yield break;
                }
            }
            finally
            {
                f.readKeyboard=keyboard; hud.readKeyboard=hudKeyboard; f.pauseOnFocusLoss=focusPause; hud.ResetFlight();
                if(focusPause && !Application.isFocused) f.SetPaused(true);
            }
        }

        private static void Click(DemoHUD hud,string path)
        {
            hud.RefreshInterface();Canvas.ForceUpdateCanvases();var target=hud.HudCanvas.transform.Find(path);
            Require(target!=null && target.gameObject.activeInHierarchy,"Visible button: "+path);
            var button=target.GetComponent<Button>();Require(button!=null && button.interactable,"Interactable button: "+path);
            var rect=button.GetComponent<RectTransform>();Vector2 screen=RectTransformUtility.WorldToScreenPoint(null,rect.TransformPoint(rect.rect.center));
            var data=new PointerEventData(EventSystem.current) { position=screen,button=PointerEventData.InputButton.Left };
            var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(data,hits);
            Require(hits.Count>0 && hits[0].gameObject==button.gameObject,"Raycast reaches button (not hidden by an overlay): "+path);
            ExecuteEvents.Execute(button.gameObject,data,ExecuteEvents.pointerClickHandler);
        }
        private static void VerifyVisibleRects(DemoHUD hud)
        {
            var canvas=hud.HudCanvas.GetComponent<RectTransform>();var bounds=canvas.rect;
            string[] paths={"TopBar","TopBar/Title","TopBar/Mode","BottomBar","BottomBar/UnlockButton","BottomBar/ResetButton","BottomBar/PauseButton","BottomBar/HelpButton","BottomBar/ExitButton"};
            foreach(var path in paths)
            {
                var rect=hud.HudCanvas.transform.Find(path).GetComponent<RectTransform>();var corners=new Vector3[4];rect.GetWorldCorners(corners);
                foreach(var corner in corners){var p=canvas.InverseTransformPoint(corner);Require(p.x>=bounds.xMin-.1f&&p.x<=bounds.xMax+.1f&&p.y>=bounds.yMin-.1f&&p.y<=bounds.yMax+.1f,"Unclipped UI rect: "+path);}
            }
        }

        public static string CheckStep5()
        {
            var f=Flight();var report=NewReport("Step 5 / actual PBR assets", "Blender procedural shaders/postprocessing are not identical to URP. Cessna 310 embedded textures and two independently animated hub pivots.");
            var world=GameObject.Find("World_HongKongIsland_PBR");var jet=f.transform.Find("VisualPivot_Cessna310/Cessna310_Imported");
            Require(world!=null && jet!=null,"Both actual models are present");
            Transform map=null;foreach(var t in world.GetComponentsInChildren<Transform>(true))if(t.name.StartsWith("HongKongIsland_PBR_Draco")){map=t;break;}Require(map!=null,"Map child present");;
            int mapTextures=CheckMaterials(map,150);int aircraftTextures=CheckMaterials(jet,10);
            Require(mapTextures>=50 && aircraftTextures>=4,"PBR textures are bound, not white proxy materials");
            report.passed.Add("PBR map and Cessna 310 supported shaders/texture bindings; texture slots="+mapTextures+" / "+aircraftTextures);
            Bounds jetBounds=LocalMeshBounds(jet,f.transform);
            Require(jetBounds.center.magnitude<.01f && Mathf.Abs(jetBounds.size.x-11.3f)<.02f && Mathf.Abs(jetBounds.size.z-9.96876f)<.02f && jetBounds.size.y<6,"Aircraft is level, real-scale and centered");
            Require(jetBounds.extents.magnitude<=f.safety.aircraftRadius,"Full aircraft including wings/tail fits safety sphere");
            report.passed.Add("Cessna 310 centered local bounds "+jetBounds.size.ToString("F3")+" fit the safety envelope");
            int corners=0;var inv=f.safety.transform.worldToLocalMatrix;
            foreach(var mf in map.GetComponentsInChildren<MeshFilter>(true))
            {
                if(mf.sharedMesh==null)continue;var b=mf.sharedMesh.bounds;var m=mf.transform.localToWorldMatrix;
                for(int i=0;i<8;i++)
                {
                    var p=m.MultiplyPoint3x4(Corner(b,i));var q=inv.MultiplyPoint3x4(p);
                    double normalized=q.x*q.x/(double)(f.safety.shieldRadii.x*f.safety.shieldRadii.x)+q.z*q.z/(double)(f.safety.shieldRadii.y*f.safety.shieldRadii.y);
                    Require(normalized<=1.00001 && q.y>=f.safety.shieldBottom && q.y<=f.safety.shieldTop,"Map geometry is contained in shield: "+mf.name);corners++;
                }
            }
            report.passed.Add(corners+" terrain/building/vegetation bounding corners contained by the configured shield");
            bool wasActive=world.activeSelf;
            try { world.SetActive(false);Require(f.safety.HitsShield(f.safety.transform.position+Vector3.up*350,f.safety.transform.position+Vector3.up*350,0),"Safety remains active when map visuals hidden"); }
            finally { world.SetActive(wasActive); }
            report.passed.Add("Hiding map visuals does not disable the analytical protection layer");
            return Save(report,"step5_asset_checks.json");
        }
        private static int CheckMaterials(Transform root,int minimumMaterials)
        {
            var materials=new HashSet<Material>();foreach(var r in root.GetComponentsInChildren<Renderer>(true))foreach(var m in r.sharedMaterials){Require(m!=null,"No missing material slot");materials.Add(m);}
            Require(materials.Count>=minimumMaterials,"Expected imported material diversity");int textures=0;
            foreach(var m in materials)
            {
                Require(m.shader!=null && m.shader.isSupported,"Supported shader: "+m.name);
                for(int i=0;i<m.shader.GetPropertyCount();i++)if(m.shader.GetPropertyType(i)==UnityEngine.Rendering.ShaderPropertyType.Texture && m.GetTexture(m.shader.GetPropertyName(i))!=null)textures++;
            }
            return textures;
        }
        private static Vector3 Corner(Bounds b,int i) { return new Vector3((i&1)==0?b.min.x:b.max.x,(i&2)==0?b.min.y:b.max.y,(i&4)==0?b.min.z:b.max.z); }
        private static Bounds LocalMeshBounds(Transform model,Transform root)
        {
            bool first=true;var bounds=new Bounds();var inverse=root.worldToLocalMatrix;
            foreach(var mf in model.GetComponentsInChildren<MeshFilter>(true))
            {
                if(mf.sharedMesh==null)continue;var matrix=inverse*mf.transform.localToWorldMatrix;
                for(int i=0;i<8;i++){var p=matrix.MultiplyPoint3x4(Corner(mf.sharedMesh.bounds,i));if(first){bounds=new Bounds(p,Vector3.zero);first=false;}else bounds.Encapsulate(p);}
            }
            Require(!first,"Model has valid mesh bounds");return bounds;
        }
        public static string CheckAll()
        {
            return CheckStep2()+"\n"+CheckStep3()+"\n"+CheckStep5()+"\n"+CheckStep4();
        }
        private static string Save(Report report,string filename)
        {
            string dir=Path.GetFullPath(Path.Combine(Application.dataPath,"../Captures/FlightDemo"));Directory.CreateDirectory(dir);
            string json=JsonUtility.ToJson(report,true);File.WriteAllText(Path.Combine(dir,filename),json);Debug.Log("[HKFlight] "+report.stage+" checks passed.");return json;
        }
    }
}
