using UnityEngine;

namespace HKFlightDemo
{
    /// <summary>Start immediately, without a logo overlay or artificial flight pause.</summary>
    public sealed class DemoStartup : MonoBehaviour
    {
        public bool enforceBorderlessFullscreen = true;
        private void Awake()
        {
#if !UNITY_EDITOR
            if (!enforceBorderlessFullscreen) return;
            int w = Display.main.systemWidth, h = Display.main.systemHeight;
            if (w > 0 && h > 0)
                Screen.SetResolution(w, h, FullScreenMode.FullScreenWindow);
#endif
        }
    }
}
