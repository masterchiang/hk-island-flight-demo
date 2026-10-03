using System;
using UnityEngine;
namespace HKFlightDemo
{
    /// <summary>Conservative closed ellipse cylinder, with analytic continuous segment checks.</summary>
    public sealed class DemoSafety : MonoBehaviour
    {
        public Vector2 shieldRadii = new Vector2(1250,660);
        public float shieldTop = 600;
        public float shieldBottom = -300;
        public Vector2 worldHalfSize = new Vector2(3600,2800);
        public float worldCeiling = 1800;
        public float minimumSeaClearance = 50;
        public float aircraftRadius = 14;
        public float margin = 6;
        public float predictionSeconds = 5;
        public bool enforceShield = true;
        public bool drawDebug = true;
        public bool ConfigurationValid => aircraftRadius>0 && margin>=0 && worldHalfSize.x>aircraftRadius+margin && worldHalfSize.y>aircraftRadius+margin && worldCeiling>aircraftRadius+margin &&
            (!enforceShield || (shieldRadii.x>0 && shieldRadii.y>0 && worldHalfSize.x>shieldRadii.x+aircraftRadius+margin && worldHalfSize.y>shieldRadii.y+aircraftRadius+margin && worldCeiling>shieldTop+2*(aircraftRadius+margin) && shieldTop>shieldBottom));
        public static bool Finite(Vector3 p) => !(float.IsNaN(p.x)||float.IsInfinity(p.x)||float.IsNaN(p.y)||float.IsInfinity(p.y)||float.IsNaN(p.z)||float.IsInfinity(p.z));
        public bool InsideWorld(Vector3 p,float radius)
        {
            p-=transform.position;
            return Finite(p) && Mathf.Abs(p.x)<worldHalfSize.x-radius && Mathf.Abs(p.z)<worldHalfSize.y-radius && p.y<worldCeiling-radius;
        }
        public bool AboveSea(Vector3 p,float radius) => p.y-transform.position.y>=minimumSeaClearance+radius;
        public bool HitsShield(Vector3 from,Vector3 to,float padding)
        {
            if(!ConfigurationValid || !Finite(from) || !Finite(to))return true;
            from-=transform.position;to-=transform.position;
            // Uniform normalized expansion is a conservative superset of the true sphere/ellipse Minkowski sum.
            double factor=1+padding/Math.Min(shieldRadii.x,shieldRadii.y);
            double ax=shieldRadii.x*factor,az=shieldRadii.y*factor;
            double start=0,end=1,dy=to.y-from.y,low=shieldBottom-padding,high=shieldTop+padding;
            if(Math.Abs(dy)<1e-10){if(from.y<low||from.y>high)return false;}
            else
            {
                double a=(low-from.y)/dy,b=(high-from.y)/dy;
                start=Math.Max(0,Math.Min(a,b));end=Math.Min(1,Math.Max(a,b));if(start>end)return false;
            }
            double x=from.x/ax,z=from.z/az,dx=(to.x-from.x)/ax,dz=(to.z-from.z)/az;
            double denom=dx*dx+dz*dz;
            double t=denom<1e-16?start:Math.Max(start,Math.Min(end,-(x*dx+z*dz)/denom));
            x+=dx*t;z+=dz*t;return x*x+z*z<=1.0000001;
        }
        public bool SegmentSafe(Vector3 from,Vector3 to,float extra=0)
        {
            float r=aircraftRadius+margin+extra;
            bool shieldSafe=!enforceShield || !HitsShield(from,to,r);
            return ConfigurationValid && InsideWorld(from,r)&&InsideWorld(to,r)&&AboveSea(from,r)&&AboveSea(to,r)&&shieldSafe;
        }
        public bool DangerAhead(Vector3 position,Vector3 forward,float speed,float extra=0)
        {
            if(!enforceShield)return false;
            Vector3 future=position+forward*(speed*predictionSeconds);
            float r=aircraftRadius+margin+extra;
            return !AboveSea(future,r)||HitsShield(position,future,r);
        }
        public Vector3 EscapeDirection(Vector3 p)
        {
            Vector3 q=p-transform.position;
            Vector3 outward=new Vector3(q.x/(shieldRadii.x*shieldRadii.x),0,q.z/(shieldRadii.y*shieldRadii.y)).normalized;
            if(outward.sqrMagnitude<.01f)outward=Vector3.back;
            return (outward+Vector3.up*(q.y<shieldTop+120?.5f:0)).normalized;
        }
        public Vector3 ConstrainCamera(Vector3 target,Vector3 desired)
        {
            desired.y=Mathf.Max(desired.y,transform.position.y+5);
            if(!enforceShield || !HitsShield(target,desired,2))return desired;
            float lo=0,hi=1;for(int i=0;i<12;i++){float mid=(lo+hi)*.5f;if(HitsShield(target,Vector3.Lerp(target,desired,mid),2))hi=mid;else lo=mid;}
            return Vector3.Lerp(target,desired,Mathf.Max(0,lo-.015f));
        }
        private void OnDrawGizmos()
        {
            if(!drawDebug)return;Gizmos.color=new Color(1,.65f,.15f,.7f);
            for(int i=0;i<64;i++)
            {
                float a=i*Mathf.PI*2/64,b=(i+1)*Mathf.PI*2/64;
                Vector3 p=new Vector3(Mathf.Cos(a)*shieldRadii.x,shieldTop,Mathf.Sin(a)*shieldRadii.y)+transform.position;
                Vector3 q=new Vector3(Mathf.Cos(b)*shieldRadii.x,shieldTop,Mathf.Sin(b)*shieldRadii.y)+transform.position;
                Gizmos.DrawLine(p,q);if(i%8==0)Gizmos.DrawLine(p,p+Vector3.down*(shieldTop-shieldBottom));
            }
            Gizmos.color=new Color(.3f,.7f,1,.35f);Gizmos.DrawWireCube(transform.position+Vector3.up*(worldCeiling+minimumSeaClearance)*.5f,
                new Vector3(worldHalfSize.x*2,worldCeiling-minimumSeaClearance,worldHalfSize.y*2));
        }
    }
}
