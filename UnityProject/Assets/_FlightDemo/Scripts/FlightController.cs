using System;
using UnityEngine;
using UnityEngine.InputSystem;
namespace HKFlightDemo
{
    [RequireComponent(typeof(Rigidbody))]
    public sealed class FlightController : MonoBehaviour
    {
        public DemoRoute route;
        public DemoSafety safety;
        public float cruiseSpeed=60,minimumSpeed=40,maximumSpeed=140;
        public float protectionPitch = 35f;
        public float protectionPitchRate = 85f;
        public float turnRate=24,pitchRate=35;
        public bool readKeyboard=true;
        public bool pauseOnFocusLoss=true;
        public bool Manual {get;private set;}
        public bool Paused {get;private set;}
        public bool Protecting {get;private set;}
        public bool Ready {get;private set;}
        public float Speed {get;private set;}
        public float Progress => route==null?0:Mathf.Repeat(distance,route.Length)/route.Length;
        public Vector3 Position {get;private set;}
        public Quaternion Rotation {get;private set;}=Quaternion.identity;
        public int ResetCount {get;private set;}
        public int ProtectionCount {get;private set;}
        public int RejectedMoves {get;private set;}
        public string Notice {get;private set;}="自动环岛巡航";
        public Vector2 ManualInput {get;set;}
        public float ThrottleInput {get;set;}
        public event Action ResetPerformed;
        private Rigidbody body;
        private float distance,yaw,pitch,roll,safeTime,noticeUntil;
        private bool resetThisFrame;
        private void Start(){Initialize();}
public void Initialize()
        {
            body=GetComponent<Rigidbody>();body.isKinematic=true;body.useGravity=false;
            Ready=route!=null&&safety!=null&&safety.ConfigurationValid&&route.radii.x>0&&route.radii.y>0;
            if(!Ready){Notice="配置错误：检查航线与安全区域";Paused=true;return;}
            route.Rebuild();
            if(route.TargetSpeed>0f){cruiseSpeed=route.TargetSpeed;maximumSpeed=Mathf.Max(maximumSpeed,cruiseSpeed*1.2f);}
            Vector3 previous;Vector3 dir;route.Evaluate(0,out previous,out dir);
            for(int i=1;i<=512;i++)
            {
                Vector3 next;route.Evaluate(route.Length*i/512,out next,out dir);
                if(!safety.SegmentSafe(previous,next,2)){Ready=false;Paused=true;Notice="配置错误：航线或起点不安全";return;}previous=next;
            }
            ResetFlight("自动环岛巡航",false);
        }
public void Unlock()
        {
            if(!Ready||Paused||Protecting)return;
            Manual=true;Vector3 f=Rotation*Vector3.forward;
            yaw=Mathf.Atan2(f.x,f.z)*Mathf.Rad2Deg;pitch=-Mathf.Asin(Mathf.Clamp(f.y,-1,1))*Mathf.Rad2Deg;
            Notice=safety!=null&&safety.enforceShield?"自由驾驶 · 安全保护保持开启":"自由驾驶 · 调试模式（保护罩关闭）";noticeUntil=Time.unscaledTime+3;
        }
        public void SetPaused(bool value){if(!Ready)return;Paused=value;ManualInput=Vector2.zero;ThrottleInput=0;}
        public void ResetFlight(string reason="已复位 · 自动环岛巡航",bool count=true)
        {
            if(!Ready||body==null)return;
            Vector3 p,f;route.Evaluate(0,out p,out f);
            if(!safety.SegmentSafe(p,p)){Ready=false;Paused=true;Notice="起点不安全，已停止演示";return;}
            Manual=false;Paused=false;Protecting=false;safeTime=0;distance=0;pitch=roll=0;
            yaw=Mathf.Atan2(f.x,f.z)*Mathf.Rad2Deg;Speed=cruiseSpeed;Position=p;Rotation=Quaternion.LookRotation(f,Vector3.up);
            ManualInput=Vector2.zero;ThrottleInput=0;body.position=p;body.rotation=Rotation;transform.SetPositionAndRotation(p,Rotation);
            if(count && !resetThisFrame)ResetCount++;resetThisFrame=true;
            Notice=reason;noticeUntil=Time.unscaledTime+3;ResetPerformed?.Invoke();
        }
private void Update()
        {
            resetThisFrame=false;
            if(!readKeyboard||!Ready)return;
            var k=Keyboard.current;if(k==null)return;
            if(!Paused&&Manual)
            {
                // User convention: W pulls the nose up; S pushes the nose down.
                ManualInput=new Vector2((k.dKey.isPressed?1:0)-(k.aKey.isPressed?1:0),(k.wKey.isPressed?1:0)-(k.sKey.isPressed?1:0));
                ThrottleInput=(k.shiftKey.isPressed?1:0)-(k.ctrlKey.isPressed?1:0);
            }
            else {ManualInput=Vector2.zero;ThrottleInput=0;}
        }
        private void FixedUpdate()
        {
            if(!Ready||Paused)return;
            Simulate(Time.fixedDeltaTime);
            if(Ready){body.MovePosition(Position);body.MoveRotation(Rotation);}
        }
        // Shared by FixedUpdate and the bounded, deterministic editor smoke checks.
        public void Simulate(float dt)
        {
            if(!Ready||Paused||dt<=0)return;
            if(dt>.05f){int steps=Mathf.CeilToInt(dt/.05f);for(int i=0;i<steps;i++)Simulate(dt/steps);return;}
            if(!safety.SegmentSafe(Position,Position)){RejectedMoves++;ResetFlight("安全状态异常 · 已返回起点");return;}
            Vector3 next;Quaternion rotation;
            if(!Manual)
            {
                distance+=cruiseSpeed*dt;Vector3 direction;route.Evaluate(distance,out next,out direction);
                float nextYaw=Mathf.Atan2(direction.x,direction.z)*Mathf.Rad2Deg;
                float bank=Mathf.Clamp(-Mathf.DeltaAngle(yaw,nextYaw)/dt*2,-25,25);
                roll=Mathf.MoveTowards(roll,bank,25*dt);yaw=nextYaw;Speed=cruiseSpeed;
                rotation=Quaternion.Euler(0,yaw,roll);
            }
            else
            {
                Speed=Mathf.Clamp(Speed+ThrottleInput*22*dt,minimumSpeed,maximumSpeed);
                float desiredYaw=yaw+ManualInput.x*turnRate*dt;
                float desiredPitch=Mathf.MoveTowards(pitch,-ManualInput.y*35,pitchRate*dt);
                float desiredRoll=Mathf.MoveTowards(roll,-ManualInput.x*40,65*dt);
                Vector3 requested=Quaternion.Euler(desiredPitch,desiredYaw,0)*Vector3.forward;
                bool danger=safety.DangerAhead(Position,requested,Speed,Protecting?100:0);
                if(danger&&!Protecting){Protecting=true;ProtectionCount++;safeTime=0;}
                if(Protecting)
                {
                    if(!danger && !safety.HitsShield(Position,Position,safety.aircraftRadius+safety.margin+120))safeTime+=dt;else safeTime=0;
                    if(safeTime>1.5f){Protecting=false;safeTime=0;}
                    else
                    {
                        // Safety takeover is a climb, not a forced turn. Preserve the current heading;
                        // only pitch up and damp roll. If this heading cannot clear the shield, the
                        // final SegmentSafe check below rejects the move and the normal reset path runs.
                        desiredYaw=yaw;
                        desiredPitch=Mathf.MoveTowards(pitch,-Mathf.Abs(protectionPitch),protectionPitchRate*dt);
                        desiredRoll=Mathf.MoveTowards(roll,0,95*dt);
                    }
                }
                yaw=desiredYaw;pitch=desiredPitch;roll=desiredRoll;
                rotation=Quaternion.Euler(pitch,yaw,roll);next=Position+rotation*Vector3.forward*(Speed*dt);
            }
            if(!safety.InsideWorld(next,safety.aircraftRadius+safety.margin))
            {RejectedMoves++;ResetFlight("到达演示边界 · 已返回起点");return;}
            if(!safety.SegmentSafe(Position,next))
            {RejectedMoves++;ResetFlight("安全保护 · 已返回起点");return;}
            Position=next;Rotation=rotation;
            if(Protecting)Notice="安全接管 · 保持航向强制拉升";
            else if(Time.unscaledTime>noticeUntil)Notice=Manual?"自由驾驶 · R 复位返回自动巡航":"自动环岛巡航";
        }
        private void OnApplicationFocus(bool focused){if(!focused&&pauseOnFocusLoss&&Ready)SetPaused(true);}
        private void OnDisable(){ManualInput=Vector2.zero;ThrottleInput=0;}
        public void SetTestPose(Vector3 p,Quaternion r,float speed)
        {
            // Intentionally explicit diagnostic entry point; never bound to a player input.
            Position=p;Rotation=r;Speed=speed;Manual=true;Paused=false;Protecting=false;safeTime=0;
            Vector3 f=r*Vector3.forward;yaw=Mathf.Atan2(f.x,f.z)*Mathf.Rad2Deg;pitch=-Mathf.Asin(Mathf.Clamp(f.y,-1,1))*Mathf.Rad2Deg;roll=0;
        }
    }
}
