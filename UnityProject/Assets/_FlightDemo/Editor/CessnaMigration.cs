using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace HKFlightDemo.Editor
{
    public static class CessnaMigration
    {
        public const string AircraftPath = "Assets/_FlightDemo/Art/Aircraft/Cessna310/Cessna310.glb";
        public static void WirePropellers(GameObject pivot, FlightController flight)
        {
            var spin = pivot.GetComponent<AircraftPropellers>() ?? Undo.AddComponent<AircraftPropellers>(pivot);
            var transforms = pivot.GetComponentsInChildren<Transform>(true);
            spin.left = transforms.Single(t => t.name == "Propeller_Left");
            spin.right = transforms.Single(t => t.name == "Propeller_Right");
            spin.flight = flight;
            spin.rpm = 1600f;
            EditorUtility.SetDirty(spin);
            // Match follow framing to the smaller 11.3 m aircraft without changing flight physics.
            var camera = UnityEngine.Object.FindAnyObjectByType<DemoOrbitCamera>();
            if (camera != null)
            {
                Undo.RecordObject(camera, "Frame Cessna aircraft");
                camera.distance = 30f;
                camera.autoDistance = 30f;
                camera.minimumDistance = 15f;
                EditorUtility.SetDirty(camera);
            }
        }
        [MenuItem("Tools/HK Flight Demo/Replace Aircraft with Cessna 310")]
        public static string Apply()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Stop Play Mode first.");
            if (SceneManager.GetActiveScene().path != "Assets/_FlightDemo/Scenes/HKFlight_Demo.unity") throw new InvalidOperationException("Open demo scene first.");
            var root = GameObject.Find("AircraftRoot");
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(AircraftPath);
            if (root == null || source == null) throw new InvalidOperationException("Aircraft root or imported Cessna missing.");
            var existing = root.transform.Find("VisualPivot_Cessna310");
            if (existing == null)
            {
                var pivot = new GameObject("VisualPivot_Cessna310");
                Undo.RegisterCreatedObjectUndo(pivot, "Create Cessna pivot");
                pivot.transform.SetParent(root.transform, false);
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(source, SceneManager.GetActiveScene());
                Undo.RegisterCreatedObjectUndo(instance, "Instantiate Cessna");
                instance.name = "Cessna310_Imported";
                instance.transform.SetParent(pivot.transform, false);
                WirePropellers(pivot, root.GetComponent<FlightController>());
                foreach (string oldName in new[] {"VisualPivot_J20_PBR", "Visual_ReplaceWithJ20"})
                {
                    var old = root.transform.Find(oldName);
                    if (old != null) Undo.DestroyObjectImmediate(old.gameObject);
                }
                existing = pivot.transform;
            }
            else WirePropellers(existing.gameObject, root.GetComponent<FlightController>());
            PlayerSettings.SplashScreen.show = false;
            PlayerSettings.SplashScreen.showUnityLogo = false;
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
            return "Cessna 310 installed; two independent propeller hubs wired; splash disabled; scene saved.";
        }
    }
}
