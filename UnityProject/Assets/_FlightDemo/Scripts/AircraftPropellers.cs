using UnityEngine;

namespace HKFlightDemo
{
    /// <summary>Two independent hub pivots, spinning around aircraft-local forward.</summary>
    public sealed class AircraftPropellers : MonoBehaviour
    {
        public Transform left;
        public Transform right;
        public FlightController flight;
        [Min(0f)] public float rpm = 1600f;
        private Quaternion leftRest, rightRest;
        private float angle;
        private void Awake()
        {
            if (flight == null) flight = GetComponentInParent<FlightController>();
            leftRest = left != null ? left.localRotation : Quaternion.identity;
            rightRest = right != null ? right.localRotation : Quaternion.identity;
        }
        private void Update() { Step(Time.deltaTime); }
        public void Step(float deltaTime)
        {
            if (deltaTime <= 0f || flight == null || !flight.Ready || flight.Paused) return;
            angle = Mathf.Repeat(angle + rpm * 6f * deltaTime, 360f);
            Quaternion spin = Quaternion.AngleAxis(angle, Vector3.forward);
            if (left != null) left.localRotation = leftRest * spin;
            if (right != null) right.localRotation = rightRest * spin;
        }
    }
}
