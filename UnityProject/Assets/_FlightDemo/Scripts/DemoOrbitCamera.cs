using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
namespace HKFlightDemo
{
    [RequireComponent(typeof(Camera))]
    public sealed class DemoOrbitCamera : MonoBehaviour
    {
        public FlightController flight;
        public float distance=46,minimumDistance=25,maximumDistance=110;
        public float elevation=13,sensitivity=.12f;
        public float autoLookAhead=100f;
        public float autoInwardLookDistance=160f;
        public float autoLookHeight=40f;
        public float autoDistance=30f;
        public Vector3 islandFocus=new Vector3(0f,150f,0f);
        [Range(0f,1f)] public float autoLookWeight=.82f;
        public float followYawOffset=-28;
        public bool readMouse=true;
        public bool FreeLook {get;private set;}
        private float orbitYaw;        private float followYaw;
        private bool lastManual;

        private bool dragging;
        private Vector3 dampVelocity;
        private void OnEnable(){if(flight!=null)flight.ResetPerformed+=Snap;}
        private void OnDisable(){if(flight!=null)flight.ResetPerformed-=Snap;Cursor.visible=true;Cursor.lockState=CursorLockMode.None;}
private void Start()
        {
            if(flight!=null){followYaw=flight.transform.eulerAngles.y+followYawOffset;lastManual=flight.Manual;}
            Snap();
        }
public void Recenter()
        {
            FreeLook=false;dragging=false;elevation=13;
            if(flight!=null&&!flight.Manual)followYaw=flight.transform.eulerAngles.y+followYawOffset;
        }

public float FieldOfView
        {
            get { return GetComponent<Camera>().fieldOfView; }
        }
        public void SetFieldOfView(float value)
        {
            GetComponent<Camera>().fieldOfView = Mathf.Clamp(value, 35f, 85f);
        }

public void Snap()
        {
            Recenter();distance=autoDistance;dampVelocity=Vector3.zero;
            if(flight!=null){followYaw=flight.transform.eulerAngles.y+followYawOffset;lastManual=flight.Manual;Place(true);}
        }
private void LateUpdate()
        {
            if(flight==null||!flight.Ready)return;
            var mouse=Mouse.current;var k=Keyboard.current;
            if(flight.Paused){dragging=false;Cursor.visible=true;Cursor.lockState=CursorLockMode.None;return;}
            if(!flight.Manual&&!FreeLook)followYaw=flight.transform.eulerAngles.y+followYawOffset;
            if(flight.Manual!=lastManual)
            {
                followYaw=flight.transform.eulerAngles.y+followYawOffset;
                if(flight.Manual)distance=autoDistance;
                lastManual=flight.Manual;dragging=false;dampVelocity=Vector3.zero;
                Place(true);
                return;
            }
            if(readMouse&&k!=null&&k.cKey.wasPressedThisFrame)Recenter();
            bool overUI=EventSystem.current!=null&&EventSystem.current.IsPointerOverGameObject();
            if(readMouse&&mouse!=null)
            {
                if(mouse.rightButton.wasPressedThisFrame&&!overUI){dragging=true;if(!FreeLook)orbitYaw=followYaw;FreeLook=true;}
                if(mouse.rightButton.wasReleasedThisFrame)dragging=false;
                if(dragging){Vector2 d=mouse.delta.ReadValue();orbitYaw+=d.x*sensitivity;elevation=Mathf.Clamp(elevation-d.y*sensitivity,-25,75);}
                if(!overUI)distance=Mathf.Clamp(distance-mouse.scroll.ReadValue().y*.035f,minimumDistance,maximumDistance);
            }
            Cursor.visible=!dragging;Cursor.lockState=dragging?CursorLockMode.Confined:CursorLockMode.None;
            Place(false);
        }
private void Place(bool snap)
        {
            Vector3 aircraftTarget=flight.transform.position+Vector3.up*2;
            bool autoIslandView=!flight.Manual&&!FreeLook;
            bool manualFollow=flight.Manual&&!FreeLook;
            float cameraDistance=(autoIslandView||manualFollow)?autoDistance:distance;
            float angle=FreeLook?orbitYaw:followYaw;
            Vector3 desired=aircraftTarget+Quaternion.Euler(elevation,angle,0)*new Vector3(0,0,-cameraDistance);
            desired=flight.safety.ConstrainCamera(aircraftTarget,desired);
            // In manual follow, write the stable offset directly: smoothing a fast aircraft target
            // makes the camera appear to zoom when A/D changes heading.
            Vector3 p=(snap||manualFollow)?desired:Vector3.SmoothDamp(transform.position,desired,ref dampVelocity,.10f);
            p=flight.safety.ConstrainCamera(aircraftTarget,p);
            Vector3 lookTarget=aircraftTarget;
            if(autoIslandView)
            {
                Vector3 inward=(flight.safety.transform.position-aircraftTarget).normalized;
                Vector3 routeDirection=flight.transform.forward;
                if(flight.route!=null){Vector3 routePoint;flight.route.Evaluate(flight.route.Length*flight.Progress,out routePoint,out routeDirection);}
                lookTarget=aircraftTarget+routeDirection*autoLookAhead+inward*autoInwardLookDistance+Vector3.up*autoLookHeight;
            }
            transform.position=p;transform.rotation=Quaternion.LookRotation(lookTarget-p,Vector3.up);
        }
    }
}
