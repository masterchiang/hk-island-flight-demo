using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace HKFlightDemo.Editor
{
    public static class FlightDemoUISetup
    {
        private const string ScenePath = "Assets/_FlightDemo/Scenes/HKFlight_Demo.unity";

        [MenuItem("Tools/HK Flight Demo/5 - Add HUD and UI")]
        public static void AddHUD()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("Stop Play Mode before adding the HUD.");
            if (SceneManager.GetActiveScene().path != ScenePath)
                throw new InvalidOperationException("Open HKFlight_Demo before adding the HUD.");
            var systems = GameObject.Find("Systems");
            if (systems == null) throw new InvalidOperationException("Systems root is missing.");
            var hud = systems.GetComponent<DemoHUD>();
            if (hud == null) hud = Undo.AddComponent<DemoHUD>(systems);
            hud.buildOnStart = true;
            hud.showKeyboardShortcuts = true;
            var flight = GameObject.Find("AircraftRoot")?.GetComponent<FlightController>();
            if (flight != null) hud.flight = flight;
            EditorUtility.SetDirty(systems);
            EditorUtility.SetDirty(hud);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
            Debug.Log("[HKFlight] HUD component added to Systems. Canvas and buttons are built at Play Mode start.");
        }
    }
}
