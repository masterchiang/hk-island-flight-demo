using UnityEngine;
namespace HKFlightDemo
{
    public sealed class DemoRoute : MonoBehaviour
    {
        public bool useCoastlinePoints = true;
        public Vector3[] coastlinePoints = new Vector3[0];
        public TextAsset coastlineRouteAsset;
        [System.Serializable] private sealed class CoastlineRoutePayload { public string source; public Vector3[] points; }

        [Header("Coastline route")]
        public bool figureEight = false;
        public Vector2 radii = new Vector2(7000f,5200f);
        public float altitude = 720f;
        [Min(1f)] public float lapDurationSeconds = 240f;
        [Range(64,2048)] public int samples = 1024;
        public bool showRoute = true;
        private float[] lengths;
        public float Length { get { Ensure(); return lengths[lengths.Length-1]; } }
        public float TargetSpeed { get { Ensure(); return lapDurationSeconds > 0f ? Length / lapDurationSeconds : 0f; } }
        public float LoopDurationSeconds { get { return lapDurationSeconds; } }

public void Rebuild()
        {
            if(useCoastlinePoints && coastlineRouteAsset!=null)
            {
                var payload=JsonUtility.FromJson<CoastlineRoutePayload>(coastlineRouteAsset.text);
                if(payload!=null && payload.points!=null && payload.points.Length>=4)coastlinePoints=payload.points;
            }
            samples=Mathf.Clamp(samples,64,2048);
            lengths=new float[samples+1]; Vector3 previous=Point(0);
            for(int i=1;i<=samples;i++){var next=Point(i/(float)samples);lengths[i]=lengths[i-1]+Vector3.Distance(previous,next);previous=next;}
        }
        private void Ensure(){if(lengths==null || lengths.Length!=samples+1)Rebuild();}
private Vector3 Point(float t)
        {
            if(useCoastlinePoints && coastlinePoints!=null && coastlinePoints.Length>=4)
            {
                float scaled=Mathf.Repeat(t,1f)*coastlinePoints.Length;int i1=Mathf.FloorToInt(scaled)%coastlinePoints.Length;int i2=(i1+1)%coastlinePoints.Length;int i0=(i1-1+coastlinePoints.Length)%coastlinePoints.Length;int i3=(i2+1)%coastlinePoints.Length;float u=scaled-Mathf.Floor(scaled);
                Vector3 p0=coastlinePoints[i0],p1=coastlinePoints[i1],p2=coastlinePoints[i2],p3=coastlinePoints[i3];
                float u2=u*u,u3=u2*u;
                return transform.position+.5f*((2f*p1)+(-p0+p2)*u+(2f*p0-5f*p1+4f*p2-p3)*u2+(-p0+3f*p1-3f*p2+p3)*u3);
            }
            float angle=t*Mathf.PI*2-Mathf.PI*.5f;float x,z;if(figureEight){x=radii.x*Mathf.Sin(angle);z=radii.y*Mathf.Sin(angle*2f);}else{x=radii.x*Mathf.Cos(angle);z=radii.y*Mathf.Sin(angle);}return transform.position+new Vector3(x,altitude,z);
        }
private Vector3 Tangent(float t)
        {
            if(useCoastlinePoints && coastlinePoints!=null && coastlinePoints.Length>=4)
            {
                float scaled=Mathf.Repeat(t,1f)*coastlinePoints.Length;int i1=Mathf.FloorToInt(scaled)%coastlinePoints.Length;int i2=(i1+1)%coastlinePoints.Length;int i0=(i1-1+coastlinePoints.Length)%coastlinePoints.Length;int i3=(i2+1)%coastlinePoints.Length;float u=scaled-Mathf.Floor(scaled),u2=u*u;
                Vector3 p0=coastlinePoints[i0],p1=coastlinePoints[i1],p2=coastlinePoints[i2],p3=coastlinePoints[i3];
                return (.5f*((-p0+p2)+(4f*p0-10f*p1+8f*p2-2f*p3)*u+(-3f*p0+9f*p1-9f*p2+3f*p3)*u2)).normalized;;;
            }
            float angle=t*Mathf.PI*2-Mathf.PI*.5f;Vector3 derivative;if(figureEight)derivative=new Vector3(radii.x*Mathf.Cos(angle),0f,2f*radii.y*Mathf.Cos(angle*2f));else derivative=new Vector3(-radii.x*Mathf.Sin(angle),0f,radii.y*Mathf.Cos(angle));return derivative.normalized;
        }
public void Evaluate(float distance,out Vector3 position,out Vector3 direction)
        {
            Ensure();float d=Mathf.Repeat(distance,Mathf.Max(.01f,Length));int lo=0,hi=samples;
            while(hi-lo>1){int m=(lo+hi)/2;if(lengths[m]<=d)lo=m;else hi=m;}
            float f=Mathf.InverseLerp(lengths[lo],lengths[hi],d);float t=(lo+f)/samples;position=Point(t);direction=Tangent(t);
        }
        private void OnDrawGizmos()
        {
            if(!showRoute)return;Gizmos.color=new Color(.2f,.85f,.9f,.75f);
            Vector3 previous=Point(0);for(int i=1;i<=256;i++){var p=Point(i/256f);Gizmos.DrawLine(previous,p);previous=p;}
        }
    }
}

