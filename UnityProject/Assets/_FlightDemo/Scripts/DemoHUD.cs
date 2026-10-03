using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace HKFlightDemo
{
    /// <summary>Small presentation HUD; one motor owns flight state, modal windows only send commands.</summary>
    public sealed class DemoHUD : MonoBehaviour
    {
        public FlightController flight;
        public bool buildOnStart = true;
        public bool showKeyboardShortcuts = true;
        public bool showPauseOverlay = false;
        public bool readKeyboard = true;
        // 背景音乐《东方之珠》。优先用 inspector 指定的 clip，为空时回退到 Resources 下的同名资源。
        public AudioClip musicClip;
        public string musicResourcePath = "PearlOfTheOrient";
        public bool playMusicOnStart = true;
        [Range(0f,1f)] public float musicVolume = .55f;
        public bool MusicPlaying => musicSource != null && musicSource.isPlaying;
        public bool ExitVisible => modal == Modal.Exit;
        public bool HelpVisible => modal == Modal.Help;
        public Canvas HudCanvas => canvas;

        private enum Modal { None, Help, Exit }
        private Modal modal;
        private bool pausedBeforeModal;
        private Canvas canvas;
        private Font font;
        private Text modeText, telemetryText, noticeText, unlockText;
        private Button unlockButton;
        private AudioSource musicSource;
        private Text musicText;
        private DemoOrbitCamera orbitCamera;
        private Slider povSlider;
        private Text povValueText;
        private GameObject pausePanel, helpPanel, exitPanel;
        private float nextTelemetryTime;
        private FlightController subscribedFlight;

        private void Awake()
        {
            if (flight == null) flight = FindAnyObjectByType<FlightController>();
            if (orbitCamera == null) orbitCamera = FindAnyObjectByType<DemoOrbitCamera>();
            if (buildOnStart) BuildInterface();
        }
        private void OnEnable()
        {
            if (flight == null) flight = FindAnyObjectByType<FlightController>();
            subscribedFlight = flight;
            if (subscribedFlight != null) subscribedFlight.ResetPerformed += OnFlightReset;
        }
        private void OnDisable()
        {
            if (subscribedFlight != null) subscribedFlight.ResetPerformed -= OnFlightReset;
            subscribedFlight = null;
            Cursor.visible = true;
            Cursor.lockState = CursorLockMode.None;
        }
        private void OnDestroy() { if (font != null) Destroy(font); }
        private void Update()
        {
            var k = Keyboard.current;
            if (readKeyboard && k != null)
            {
                // Only the topmost context consumes each shortcut. In particular Esc cannot open two states.
                if (k.escapeKey.wasPressedThisFrame)
                {
                    if (ExitVisible) CloseExit();
                    else if (HelpVisible) ToggleHelp();
                    else TogglePause();
                }
                else if (k.rKey.wasPressedThisFrame) ResetFlight();
                else if (k.f1Key.wasPressedThisFrame && !ExitVisible) ToggleHelp();
                else if (k.tabKey.wasPressedThisFrame && modal == Modal.None) ToggleFlightMode();
            }
            RefreshInterface();
        }

        public void BuildInterface()
        {
            if (canvas != null) return;
            if (EventSystem.current == null)
            {
                var es = new GameObject("FlightDemo_EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule));
                es.transform.SetParent(transform, false);
                es.GetComponent<InputSystemUIInputModule>().AssignDefaultActions();
            }
            // Use the Windows system font, rather than silently bundling/licensing a system font file.
            font = Font.CreateDynamicFontFromOSFont(new[] { "Microsoft YaHei UI", "Microsoft YaHei", "Arial" }, 24);
            if (font == null) font = new Font("Arial");
            var go = new GameObject("FlightDemo_HUD_Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            go.transform.SetParent(transform, false);
            canvas = go.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 100;
            var scaler = go.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = .5f;

            var top = Panel("TopBar", canvas.transform, new Color(.018f,.043f,.063f,.90f));
            Bar(top.GetComponent<RectTransform>(), true, 104);
            var title = Label("Title", top.transform, "香港岛  /  J-20 飞行演示", 29, Color.white, TextAnchor.MiddleLeft);
            Fixed(title.rectTransform, new Vector2(0,1), new Vector2(0,1), new Vector2(28,-14), new Vector2(780,40));
            modeText = Label("Mode", top.transform, "自动环岛巡航", 25, new Color(.34f,.9f,.95f), TextAnchor.MiddleRight);
            Fixed(modeText.rectTransform, Vector2.one, Vector2.one, new Vector2(-28,-14), new Vector2(370,40));
            telemetryText = Label("Telemetry", top.transform, "正在启动飞行系统…", 22, new Color(.75f,.86f,.9f), TextAnchor.MiddleLeft);
            Stretch(telemetryText.rectTransform, new Vector2(28,12), new Vector2(-28,-54));
            povValueText = Label("POVValue", top.transform, "POV 55°", 18, new Color(.75f,.86f,.9f), TextAnchor.MiddleRight);
            Fixed(povValueText.rectTransform, new Vector2(1,0), new Vector2(1,0), new Vector2(-260,16), new Vector2(100,24));
            povSlider = CreatePOVSlider(top.transform);;

            // 展示用署名与国庆祝贺（本次展示需求新增，纯展示文本，不参与任何逻辑）
            var author = Label("Author", top.transform, "项目作者:github.com/masterchiang", 26, new Color(1f,.13f,.10f), TextAnchor.MiddleLeft);
            Fixed(author.rectTransform, new Vector2(.345f,1), new Vector2(0,1), new Vector2(0,-10), new Vector2(700,46));
            var buildCredit = Label("BuildCredit", top.transform, "代码构建：Atria Dawn LLM", 26, new Color(1f,.82f,.15f), TextAnchor.MiddleLeft);
            Fixed(buildCredit.rectTransform, new Vector2(.345f,1), new Vector2(0,1), new Vector2(0,-56), new Vector2(700,42));
            var nationalDay = Label("NationalDay", top.transform, "祝贺国庆77周年", 28, new Color(1f,.13f,.10f), TextAnchor.MiddleCenter);
            Fixed(nationalDay.rectTransform, new Vector2(.79f,1), new Vector2(.5f,1), new Vector2(0,-10), new Vector2(360,46));

            BuildBackgroundMusic();

            var notice = Panel("NoticeBox", canvas.transform, new Color(.026f,.105f,.13f,.8f));
            Fixed(notice.GetComponent<RectTransform>(), new Vector2(.5f,1), new Vector2(.5f,1), new Vector2(0,-142), new Vector2(760,48));
            noticeText = Label("Notice", notice.transform, "自动环岛巡航", 22, new Color(.6f,1,.86f), TextAnchor.MiddleCenter);
            Stretch(noticeText.rectTransform, new Vector2(12,4), new Vector2(-12,-4));

            var bottom = Panel("BottomBar", canvas.transform, new Color(.018f,.043f,.063f,.92f));
            Bar(bottom.GetComponent<RectTransform>(), false, 124);
            var hint = Label("Hint", bottom.transform, showKeyboardShortcuts ? "右键观察  /  滚轮缩放  /  C 回正  /  WASD 驾驶  /  Shift·Ctrl 速度  /  R 复位  /  Esc 暂停" : "", 20, new Color(.68f,.8f,.85f), TextAnchor.MiddleCenter);
            Stretch(hint.rectTransform, new Vector2(18,82), new Vector2(-18,-10));
            // 6 个按钮均分底栏；背景音乐开关放在"帮助"和"退出"之间。
            unlockButton = ActionButton("UnlockButton", bottom.transform, "解锁驾驶", .085f, ToggleFlightMode, true);
            unlockText = unlockButton.GetComponentInChildren<Text>();
            ActionButton("ResetButton", bottom.transform, "一键复位", .25f, ResetFlight);
            ActionButton("PauseButton", bottom.transform, "暂停", .4167f, TogglePause);
            ActionButton("HelpButton", bottom.transform, "帮助", .5833f, ToggleHelp);
            var musicButton = ActionButton("MusicButton", bottom.transform, "关闭背景音乐", .75f, ToggleMusic);
            musicText = musicButton.GetComponentInChildren<Text>();
            ActionButton("ExitButton", bottom.transform, "退出", .9167f, OpenExit);

            pausePanel = ModalPanel("PauseOverlay", "飞行已暂停", "切出窗口会暂停飞行。点击继续后恢复驾驶。", 420);
            var pauseCard = pausePanel.transform.Find("Card");
            DialogButton("ResumeButton", pauseCard, "继续飞行", -.25f, Resume, true);
            DialogButton("ResetButton", pauseCard, "复位巡航", 0, ResetFlight);
            DialogButton("ExitButton", pauseCard, "退出", .25f, OpenExit);

            helpPanel = ModalPanel("HelpPanel", "操作说明", "右键拖动：自由观察；滚轮：镜头远近\nPOV 滑块：调整并显示相机视场角\nC：镜头回正；相机独立于飞机转向\nW：抬高机头；S：压低机头\nA / D：左右转向\nShift / Ctrl：加速 / 减速\nTab：解锁驾驶；手动时复位返回自动巡航\nR：一键复位；Esc：关闭当前窗口\n背景音乐：点底部「关闭背景音乐 / 开启背景音乐」按钮切换\n\n海平面以下与世界边界会自动复位；切出窗口不会自动暂停飞行。", 680);;
            DialogButton("CloseHelp", helpPanel.transform.Find("Card"), "返回", 0, ToggleHelp, true);

            exitPanel = ModalPanel("ExitPanel", "退出飞行演示？", "取消后恢复打开此窗口之前的运行或暂停状态。", 340);
            DialogButton("Confirm", exitPanel.transform.Find("Card"), "确认退出", -.18f, ConfirmExit);
            DialogButton("Cancel", exitPanel.transform.Find("Card"), "取消", .18f, CloseExit, true);
            pausePanel.SetActive(false); helpPanel.SetActive(false); exitPanel.SetActive(false);
            RefreshInterface();
        }

        public void ToggleFlightMode()
        {
            if (flight == null || !flight.Ready || flight.Paused || flight.Protecting || modal != Modal.None) return;
            if (flight.Manual) ResetFlight(); else flight.Unlock();
            RefreshInterface();
        }
        public void ResetFlight()
        {
            modal = Modal.None;
            if (flight != null) flight.ResetFlight("已复位 · 自动环岛巡航");
            RefreshInterface();
        }
        private void OnFlightReset() { modal = Modal.None; nextTelemetryTime = 0; RefreshInterface(); }
        public void TogglePause()
        {
            if (flight == null || !flight.Ready || modal != Modal.None) return;
            flight.SetPaused(!flight.Paused);
            RefreshInterface();
        }
        public void Resume()
        {
            if (flight == null || !flight.Ready || modal != Modal.None) return;
            flight.SetPaused(false); RefreshInterface();
        }
        // 背景音乐：独立 AudioSource，2D 播放、循环，不参与暂停/复位逻辑。
        private void BuildBackgroundMusic()
        {
            if (musicClip == null && !string.IsNullOrEmpty(musicResourcePath))
                musicClip = Resources.Load<AudioClip>(musicResourcePath);
            var go = new GameObject("FlightDemo_BGM", typeof(AudioSource));
            go.transform.SetParent(transform, false);
            musicSource = go.GetComponent<AudioSource>();
            musicSource.clip = musicClip;
            musicSource.loop = true;
            musicSource.playOnAwake = false;
            musicSource.spatialBlend = 0f;
            musicSource.volume = musicVolume;
            musicSource.priority = 64;
            if (musicClip == null) Debug.LogWarning("[DemoHUD] 背景音乐未找到：Resources/" + musicResourcePath + " 或 inspector 未指定 musicClip。");
            else if (playMusicOnStart) musicSource.Play();
            RefreshMusicLabel();
        }
        public void ToggleMusic() { SetMusic(!MusicPlaying); }
        public void SetMusic(bool on)
        {
            if (musicSource != null && musicSource.clip != null)
            {
                if (on) { if (!musicSource.isPlaying) { musicSource.volume = musicVolume; musicSource.Play(); } }
                else if (musicSource.isPlaying) musicSource.Pause();
            }
            RefreshMusicLabel();
        }
        private void RefreshMusicLabel()
        {
            if (musicText == null) return;
            string label = MusicPlaying ? "关闭背景音乐" : "开启背景音乐";
            if (musicText.text != label) musicText.text = label;
        }
        public void ToggleHelp()
        {
            if (flight == null || modal == Modal.Exit) return;
            if (HelpVisible)
            {
                modal = Modal.None; flight.SetPaused(pausedBeforeModal);
            }
            else
            {
                pausedBeforeModal = flight.Paused; modal = Modal.Help; flight.SetPaused(true);
            }
            RefreshInterface();
        }
        public void OpenExit()
        {
            if (flight == null || ExitVisible) return;
            if (HelpVisible) { modal = Modal.None; flight.SetPaused(pausedBeforeModal); }
            pausedBeforeModal = flight.Paused; modal = Modal.Exit; flight.SetPaused(true);
            RefreshInterface();
        }
        public void CloseExit()
        {
            if (!ExitVisible || flight == null) return;
            modal = Modal.None; flight.SetPaused(pausedBeforeModal); RefreshInterface();
        }
        public void ConfirmExit()
        {
            // Input/scene state cannot bypass the confirmation modal.
            if (!ExitVisible) return;
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit();
#endif
        }
        public void RefreshInterface()
        {
            if (canvas == null || flight == null) return;
            RefreshMusicLabel();
            string mode = !flight.Ready ? "飞行系统未就绪" : flight.Paused ? "已暂停" : flight.Protecting ? "自动保护接管" : flight.Manual ? "自由驾驶" : "自动环岛巡航";
            modeText.text = mode;
            noticeText.text = flight.Notice;
            noticeText.color = flight.Protecting ? new Color(1,.8f,.35f) : new Color(.6f,1,.86f);
            unlockText.text = flight.Protecting ? "自动避让中" : flight.Manual ? "复位至自动巡航" : "解锁驾驶";
            unlockButton.interactable = flight.Ready && !flight.Paused && !flight.Protecting && modal == Modal.None;
            if (povSlider != null && orbitCamera != null) povSlider.SetValueWithoutNotify(orbitCamera.FieldOfView);
            if (povValueText != null && orbitCamera != null) povValueText.text = string.Format("POV {0:0}°",orbitCamera.FieldOfView);;
            if (Time.unscaledTime >= nextTelemetryTime)
            {
                string progress = flight.Manual ? "自由飞行" : string.Format("航线 {0:0}%",flight.Progress*100);
                telemetryText.text = string.Format("速度 {0:0} km/h   ·   海拔 {1:0} m   ·   航向 {2:000}°   ·   {3}", flight.Speed*3.6f,flight.Position.y,flight.Rotation.eulerAngles.y,progress);
                nextTelemetryTime = Time.unscaledTime + .15f;
            }
            pausePanel?.SetActive(showPauseOverlay && flight.Paused && modal == Modal.None);;
            helpPanel?.SetActive(HelpVisible);
            exitPanel?.SetActive(ExitVisible);
        }

        private GameObject ModalPanel(string name,string title,string body,float height)
        {
            var overlay=Panel(name,canvas.transform,new Color(.006f,.015f,.025f,.72f));
            Stretch(overlay.GetComponent<RectTransform>(),Vector2.zero,Vector2.zero);
            var card=Panel("Card",overlay.transform,new Color(.024f,.064f,.088f,.99f));
            Fixed(card.GetComponent<RectTransform>(),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(800,height));
            var header=Label("Header",card.transform,title,32,Color.white,TextAnchor.MiddleCenter);
            Fixed(header.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-25),new Vector2(736,48));
            var content=Label("Body",card.transform,body,23,new Color(.78f,.88f,.92f),TextAnchor.UpperLeft);
            Stretch(content.rectTransform,new Vector2(32,102),new Vector2(-32,-95));
            return overlay;
        }
        private Button ActionButton(string name,Transform parent,string text,float x,UnityEngine.Events.UnityAction action,bool primary=false)
        {
            var b=MakeButton(name,parent,text,action,primary);
            Fixed(b.GetComponent<RectTransform>(),new Vector2(x,0),new Vector2(.5f,0),new Vector2(0,20),new Vector2(210,52));
            return b;
        }
        private void DialogButton(string name,Transform parent,string text,float x,UnityEngine.Events.UnityAction action,bool primary=false)
        {
            var b=MakeButton(name,parent,text,action,primary);
            Fixed(b.GetComponent<RectTransform>(),new Vector2(.5f+x,0),new Vector2(.5f,0),new Vector2(0,26),new Vector2(180,52));
        }
        private Slider CreatePOVSlider(Transform parent)
        {
            var go=new GameObject("POVSlider",typeof(RectTransform),typeof(Slider));go.transform.SetParent(parent,false);
            Fixed(go.GetComponent<RectTransform>(),new Vector2(1,0),new Vector2(1,0),new Vector2(-130,18),new Vector2(120,22));
            var background=Panel("Background",go.transform,new Color(.18f,.32f,.38f,.9f));Stretch(background.GetComponent<RectTransform>(),new Vector2(0,.35f),new Vector2(1,.65f));
            var handle=Panel("Handle",go.transform,new Color(.35f,.9f,.95f,1f));Fixed(handle.GetComponent<RectTransform>(),new Vector2(0,.5f),new Vector2(0,.5f),Vector2.zero,new Vector2(16,28));
            var slider=go.GetComponent<Slider>();slider.minValue=35f;slider.maxValue=85f;slider.wholeNumbers=true;slider.fillRect=null;slider.handleRect=handle.GetComponent<RectTransform>();slider.targetGraphic=handle.GetComponent<Image>();
            slider.value=orbitCamera!=null?orbitCamera.FieldOfView:55f;slider.onValueChanged.AddListener(SetPOV);return slider;
        }
        private void SetPOV(float value)
        {
            if(orbitCamera!=null)orbitCamera.SetFieldOfView(value);
            if(povValueText!=null)povValueText.text=string.Format("POV {0:0}°",value);
        }
        private Button MakeButton(string name,Transform parent,string text,UnityEngine.Events.UnityAction action,bool primary)
        {
            var go=Panel(name,parent,primary?new Color(.04f,.42f,.52f):new Color(.10f,.22f,.29f));
            var b=go.AddComponent<Button>();b.targetGraphic=go.GetComponent<Image>();b.onClick.AddListener(action);
            var colors=b.colors;colors.highlightedColor=new Color(.75f,1,1);colors.disabledColor=new Color(.38f,.48f,.52f,.7f);b.colors=colors;
            var label=Label("Text",go.transform,text,22,Color.white,TextAnchor.MiddleCenter);
            Stretch(label.rectTransform,new Vector2(5,5),new Vector2(-5,-5));
            return b;
        }
        private GameObject Panel(string name,Transform parent,Color color)
        {
            var go=new GameObject(name,typeof(RectTransform),typeof(Image));go.transform.SetParent(parent,false);
            go.GetComponent<Image>().color=color;return go;
        }
        private Text Label(string name,Transform parent,string text,int size,Color color,TextAnchor align)
        {
            var go=new GameObject(name,typeof(RectTransform),typeof(Text));go.transform.SetParent(parent,false);
            var label=go.GetComponent<Text>();label.font=font;label.fontSize=size;label.color=color;label.alignment=align;label.text=text;
            label.raycastTarget=false;label.horizontalOverflow=HorizontalWrapMode.Wrap;label.verticalOverflow=VerticalWrapMode.Truncate;
            return label;
        }
        private static void Stretch(RectTransform rect,Vector2 min,Vector2 max)
        {
            rect.anchorMin=Vector2.zero;rect.anchorMax=Vector2.one;rect.pivot=new Vector2(.5f,.5f);rect.offsetMin=min;rect.offsetMax=max;rect.localScale=Vector3.one;
        }
        private static void Fixed(RectTransform rect,Vector2 anchor,Vector2 pivot,Vector2 position,Vector2 size)
        {
            rect.anchorMin=rect.anchorMax=anchor;rect.pivot=pivot;rect.anchoredPosition=position;rect.sizeDelta=size;rect.localScale=Vector3.one;
        }
        private static void Bar(RectTransform rect,bool top,float height)
        {
            rect.anchorMin=new Vector2(0,top?1:0);rect.anchorMax=new Vector2(1,top?1:0);rect.pivot=new Vector2(.5f,top?1:0);
            rect.anchoredPosition=new Vector2(0,top?-20:20);rect.sizeDelta=new Vector2(-40,height);rect.localScale=Vector3.one;
        }
    }
}
