using UnityEngine;
using UnityEngine.UI;

namespace HKFlightDemo
{
    /// <summary>
    /// 启动流程：先把显示模式规范成"全屏无边框 + 跟随显示器原生分辨率"，
    /// 再全屏展示 LOGO 图并保持 holdSeconds 秒（期间暂停飞行），淡出后进入 DEMO。
    /// Unity 官方启动画面不受本脚本影响，仍在它之前播放。
    /// </summary>
    public sealed class DemoStartup : MonoBehaviour
    {
        public FlightController flight;
        public Texture2D logoTexture;
        public string logoResourcePath = "LOGO";
        public bool showLogoOnStart = true;
        [Min(0f)] public float holdSeconds = 2.5f;
        [Min(0f)] public float fadeSeconds = .3f;
        [Range(.1f,1f)] public float logoMaxScreenFraction = 1f;
        public Color backdropColor = Color.black;
        public bool pauseFlightDuringLogo = true;
        public bool enforceBorderlessFullscreen = true;

        private Canvas canvas;
        private CanvasGroup group;
        private bool flightPausedByLogo;
        private float shownAt = -1f;

        private void Awake()
        {
            if (flight == null) flight = FindAnyObjectByType<FlightController>();
            if (enforceBorderlessFullscreen) ApplyBorderlessFullscreen();
            if (showLogoOnStart) BuildOverlay();
        }

        // 只在打包后的 Player 里强制，编辑器内不动 Game 视图，方便调试。
        private void ApplyBorderlessFullscreen()
        {
#if !UNITY_EDITOR
            int w = Display.main.systemWidth, h = Display.main.systemHeight;
            if (w <= 0 || h <= 0) return;
            if (Screen.fullScreenMode != FullScreenMode.FullScreenWindow || Screen.width != w || Screen.height != h)
                Screen.SetResolution(w, h, FullScreenMode.FullScreenWindow);
#endif
        }

        private void BuildOverlay()
        {
            if (logoTexture == null && !string.IsNullOrEmpty(logoResourcePath))
                logoTexture = Resources.Load<Texture2D>(logoResourcePath);
            if (logoTexture == null)
                Debug.LogWarning("[DemoStartup] 未找到 LOGO：Resources/" + logoResourcePath + " 或 inspector 未指定 logoTexture。");

            var go = new GameObject("FlightDemo_Logo_Canvas", typeof(Canvas), typeof(GraphicRaycaster), typeof(CanvasGroup));
            go.transform.SetParent(transform, false);
            canvas = go.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 500;                 // 高于 HUD(100)，保证盖在最上层
            group = go.GetComponent<CanvasGroup>();

            var backdrop = NewImage("Backdrop", go.transform, backdropColor);
            Full(backdrop.rectTransform);              // raycastTarget 默认开：LOGO 期间挡住误点击

            if (logoTexture != null)
            {
                var holder = new GameObject("Logo", typeof(RectTransform), typeof(RawImage));
                holder.transform.SetParent(go.transform, false);
                var rect = holder.GetComponent<RectTransform>();
                Full(rect);
                float f = Mathf.Clamp(logoMaxScreenFraction, .1f, 1f);
                if (f < 1f)
                {
                    float m = (1f - f) * .5f;
                    rect.anchorMin = new Vector2(m, m);
                    rect.anchorMax = new Vector2(1f - m, 1f - m);
                    rect.offsetMin = rect.offsetMax = Vector2.zero;
                }
                var raw = holder.GetComponent<RawImage>();
                raw.texture = logoTexture;
                raw.raycastTarget = false;
                var fit = holder.AddComponent<AspectRatioFitter>();
                fit.aspectMode = AspectRatioFitter.AspectMode.FitInParent;
                fit.aspectRatio = (float)logoTexture.width / logoTexture.height;
            }
            shownAt = -1f;
        }

        private void Update()
        {
            if (canvas == null) return;
            // 等 FlightController 就绪后再暂停，避免它自己的 Start() 把暂停状态覆盖掉。
            if (pauseFlightDuringLogo && !flightPausedByLogo && flight != null && flight.Ready)
            {
                flight.SetPaused(true);
                flightPausedByLogo = true;
            }
            if (shownAt < 0f) { shownAt = Time.unscaledTime; return; }
            float elapsed = Time.unscaledTime - shownAt;
            if (elapsed < holdSeconds) return;
            float k = fadeSeconds > 0f ? Mathf.Clamp01((elapsed - holdSeconds) / fadeSeconds) : 1f;
            if (group != null) group.alpha = 1f - k;
            if (k >= 1f) Finish();
        }

        private void Finish()
        {
            if (flightPausedByLogo && flight != null) flight.SetPaused(false);
            flightPausedByLogo = false;
            if (canvas != null) Destroy(canvas.gameObject);
            canvas = null; group = null;
            enabled = false;
        }

        private void OnDisable()
        {
            if (flightPausedByLogo && flight != null) flight.SetPaused(false);
            flightPausedByLogo = false;
        }

        private static Image NewImage(string name, Transform parent, Color color)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image));
            go.transform.SetParent(parent, false);
            var img = go.GetComponent<Image>();
            img.color = color;
            return img;
        }
        private static void Full(RectTransform rect)
        {
            rect.anchorMin = Vector2.zero; rect.anchorMax = Vector2.one;
            rect.pivot = new Vector2(.5f, .5f);
            rect.offsetMin = rect.offsetMax = Vector2.zero;
            rect.localScale = Vector3.one;
        }
    }
}
