using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace HKFlightDemo.Editor
{
    public static class FlightDemoSetup
    {
        [MenuItem("Tools/HK Flight Demo/2 - Attach Flight Systems")]
        public static void Attach()
        {
            if(Application.isPlaying)throw new InvalidOperationException("Stop Play Mode first.");
            if(SceneManager.GetActiveScene().path!=FlightDemoSceneBuilder.ScenePath)throw new InvalidOperationException("Open HKFlight_Demo first.");
            var route=Get<DemoRoute>("Route");var safety=Get<DemoSafety>("Safety");var flight=Get<FlightController>("AircraftRoot");
            flight.route=route;flight.safety=safety;
            var camera=Get<DemoOrbitCamera>("Main Camera");camera.flight=flight;
            EditorUtility.SetDirty(route);EditorUtility.SetDirty(safety);EditorUtility.SetDirty(flight);EditorUtility.SetDirty(camera);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
            Debug.Log("[HKFlight] Flight, safety and orbit camera wired and saved. Press Play to verify.");
        }
        private static T Get<T>(string name) where T:Component
        {
            var go=GameObject.Find(name);if(go==null)throw new InvalidOperationException("Missing scene object: "+name);
            var component=go.GetComponent<T>();return component!=null?component:Undo.AddComponent<T>(go);
        }
    }
}
