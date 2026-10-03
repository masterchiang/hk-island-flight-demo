using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace HKFlightDemo.Editor
{
    /// <summary>Integrates the supplied PBR world and J-20 into the one-off demo scene.</summary>
    public static class FlightDemoAssetIntegrator
    {
        private const string ScenePath = "Assets/_FlightDemo/Scenes/HKFlight_Demo.unity";
        private const string WorldAssetPath = "Assets/_FlightDemo/Art/World/HongKongIsland_PBR_Draco.glb";
        private const string AircraftAssetPath = "Assets/_FlightDemo/Art/Aircraft/J20_ChineseChengdu_CC_BY_4_0/scene.gltf";
        private const string WorldRootName = "World_HongKongIsland_PBR";
        private const string AircraftVisualName = "VisualPivot_J20_PBR";

        [MenuItem("Tools/HK Flight Demo/3 - Integrate PBR Island and J-20")]
        public static void Integrate()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("Stop Play Mode before integrating the models.");
            if (SceneManager.GetActiveScene().path != ScenePath)
                throw new InvalidOperationException("Open HKFlight_Demo before integrating the models.");

            GameObject worldAsset = AssetDatabase.LoadAssetAtPath<GameObject>(WorldAssetPath);
            GameObject aircraftAsset = AssetDatabase.LoadAssetAtPath<GameObject>(AircraftAssetPath);
            if (worldAsset == null || aircraftAsset == null)
                throw new InvalidOperationException("The PBR GLB or J-20 GLTF asset is missing or has not finished importing.");

            GameObject worldPlaceholder = GameObject.Find("World_Placeholder_ReplaceWithHKIsland");
            GameObject aircraftRoot = GameObject.Find("AircraftRoot");
            GameObject safetyObject = GameObject.Find("Safety");
            GameObject routeObject = GameObject.Find("Route");
            if (worldPlaceholder == null || aircraftRoot == null || safetyObject == null || routeObject == null)
                throw new InvalidOperationException("The expected demo roots are missing. No scene changes were made.");
            if (GameObject.Find(WorldRootName) != null || aircraftRoot.transform.Find(AircraftVisualName) != null)
                throw new InvalidOperationException("Real models are already present. Refusing to duplicate them.");

            var safety = safetyObject.GetComponent<DemoSafety>();
            var route = routeObject.GetComponent<DemoRoute>();
            var flight = aircraftRoot.GetComponent<FlightController>();
            if (safety == null || route == null || flight == null)
                throw new InvalidOperationException("Flight/safety components are missing. No scene changes were made.");

            int undoGroup = Undo.GetCurrentGroup();
            Undo.SetCurrentGroupName("Integrate PBR Hong Kong Island and J-20");
            GameObject worldRoot = null;
            GameObject worldInstance = null;
            GameObject aircraftPivot = null;
            GameObject aircraftInstance = null;
            try
            {
                worldRoot = new GameObject(WorldRootName);
                Undo.RegisterCreatedObjectUndo(worldRoot, "Create PBR island root");
                worldRoot.transform.position = new Vector3(-2498.75f, 0f, -3256.61f);

                worldInstance = PrefabUtility.InstantiatePrefab(worldAsset, SceneManager.GetActiveScene()) as GameObject;
                if (worldInstance == null) throw new InvalidOperationException("Unity could not instantiate the imported PBR island GLB.");
                Undo.RegisterCreatedObjectUndo(worldInstance, "Instantiate PBR island");
                worldInstance.name = "HongKongIsland_PBR_Draco";
                worldInstance.transform.SetParent(worldRoot.transform, false);

                // The Blender map intentionally omits its 96 km environment plane. Recreate a bounded harbor water surface.
                var water = CreateHarborWater(worldRoot.transform);
                Undo.RegisterCreatedObjectUndo(water, "Create harbor water surface");

                aircraftPivot = new GameObject(AircraftVisualName);
                Undo.RegisterCreatedObjectUndo(aircraftPivot, "Create J-20 visual pivot");
                aircraftPivot.transform.SetParent(aircraftRoot.transform, false);

                aircraftInstance = PrefabUtility.InstantiatePrefab(aircraftAsset, SceneManager.GetActiveScene()) as GameObject;
                if (aircraftInstance == null) throw new InvalidOperationException("Unity could not instantiate the imported textured J-20 GLTF.");
                Undo.RegisterCreatedObjectUndo(aircraftInstance, "Instantiate J-20");
                aircraftInstance.name = "J20_ChineseChengdu_Imported_PBR";
                aircraftInstance.transform.SetParent(aircraftPivot.transform, false);
                NormalizeAircraft(aircraftInstance.transform, aircraftAsset.transform.localRotation);

                Transform oldProxy = aircraftRoot.transform.Find("Visual_ReplaceWithJ20");
                if (oldProxy != null) Undo.RecordObject(oldProxy.gameObject, "Disable aircraft proxy");
                Undo.RecordObject(worldPlaceholder, "Disable island proxy");
                worldPlaceholder.SetActive(false);
                if (oldProxy != null) oldProxy.gameObject.SetActive(false);

                // The island's exported world-space bounds are 14.9 km x 11.2 km with terrain/buildings up to 596.7 m.
                // Keep safety and route values in the same Unity-meters coordinate system as the imported GLB.
                safety.shieldRadii = new Vector2(10800f, 7900f);
                safety.shieldBottom = -20f;
                safety.shieldTop = 660f;
                safety.worldHalfSize = new Vector2(13500f, 10000f);
                safety.worldCeiling = 2200f;
                safety.minimumSeaClearance = 50f;
                safety.aircraftRadius = 14f;
                safety.margin = 6f;
                safety.predictionSeconds = 5f;

                route.radii = new Vector2(11200f, 8200f);
                route.altitude = 820f;
                route.Rebuild();
                flight.cruiseSpeed = 60f;
                flight.minimumSpeed = 40f;
                flight.maximumSpeed = 140f;
                flight.route = route;
                flight.safety = safety;

                EditorUtility.SetDirty(worldRoot);
                EditorUtility.SetDirty(aircraftPivot);
                EditorUtility.SetDirty(safety);
                EditorUtility.SetDirty(route);
                EditorUtility.SetDirty(flight);
                EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
                EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
                Undo.CollapseUndoOperations(undoGroup);
                Debug.Log("[HKFlight] PBR island and textured J-20 integrated. 155 map PBR materials / 82 embedded textures; 85 aircraft materials / 32 texture slots. Island proxy and aircraft proxy are preserved but inactive.");
            }
            catch
            {
                if (aircraftInstance != null) Undo.DestroyObjectImmediate(aircraftInstance);
                if (aircraftPivot != null) Undo.DestroyObjectImmediate(aircraftPivot);
                if (worldRoot != null) Undo.DestroyObjectImmediate(worldRoot);
                throw;
            }
        }

[MenuItem("Tools/HK Flight Demo/4 - Align J-20 Nose with Flight Direction")]
        public static void AlignJ20Forward()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("Stop Play Mode before aligning the aircraft.");
            if (SceneManager.GetActiveScene().path != ScenePath)
                throw new InvalidOperationException("Open HKFlight_Demo before aligning the aircraft.");
            GameObject aircraftRoot = GameObject.Find("AircraftRoot");
            Transform jet = aircraftRoot != null ? aircraftRoot.transform.Find(AircraftVisualName + "/J20_ChineseChengdu_Imported_PBR") : null;
            if (jet == null) throw new InvalidOperationException("The integrated J-20 model was not found.");
            Undo.RecordObject(jet, "Align J-20 with flight direction");
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(AircraftAssetPath);
            if (source == null) throw new InvalidOperationException("The source J-20 prefab is missing.");
            NormalizeAircraft(jet, source.transform.localRotation);
            EditorUtility.SetDirty(jet);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
            Debug.Log("[HKFlight] J-20 nose aligned to the FlightController forward direction (+Z local).");
        }


        private static void NormalizeAircraft(Transform jet, Quaternion importedBasis)
        {
            // Preserve the importer's -90 degree X basis. Replacing it with only Y=180 stood the jet upright.
            jet.localRotation = Quaternion.Euler(0, 180, 0) * importedBasis;
            jet.localScale = Vector3.one * (20f / 859.97f);
            jet.localPosition = Vector3.zero;
            var inverse = jet.parent.worldToLocalMatrix;
            bool first = true;
            Bounds bounds = new Bounds();
            foreach (var filter in jet.GetComponentsInChildren<MeshFilter>(true))
            {
                if (filter.sharedMesh == null) continue;
                Bounds b = filter.sharedMesh.bounds;
                Matrix4x4 matrix = inverse * filter.transform.localToWorldMatrix;
                for (int i = 0; i < 8; i++)
                {
                    Vector3 corner = new Vector3((i & 1) == 0 ? b.min.x : b.max.x,
                        (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z);
                    Vector3 point = matrix.MultiplyPoint3x4(corner);
                    if (first) { bounds = new Bounds(point, Vector3.zero); first = false; }
                    else bounds.Encapsulate(point);
                }
            }
            if (first) throw new InvalidOperationException("The J-20 has no valid mesh bounds.");
            jet.localPosition = -bounds.center;
            Debug.Log("[HKFlight] Centered J-20 bounds (meters): " + bounds.size + "; preserved importer basis.");
        }

        private static GameObject CreateHarborWater(Transform parent)
        {
            string materialPath = "Assets/_FlightDemo/Art/World/HarborWater.mat";
            string meshPath = "Assets/_FlightDemo/Art/World/HarborWaterMesh.asset";
            Material material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            if (material == null)
            {
                Shader shader = Shader.Find("Universal Render Pipeline/Lit");
                if (shader == null) throw new InvalidOperationException("URP/Lit shader is unavailable for the harbor water.");
                material = new Material(shader) { name = "HarborWater" };
                material.SetColor("_BaseColor", new Color(0.025f, 0.19f, 0.24f, 1f));
                material.SetFloat("_Metallic", 0.24f);
                material.SetFloat("_Smoothness", 0.84f);
                AssetDatabase.CreateAsset(material, materialPath);
            }
            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
            if (mesh == null)
            {
                mesh = new Mesh { name = "HarborWaterMesh" };
                mesh.vertices = new[]
                {
                    new Vector3(-15000f, 0f, -12000f), new Vector3(15000f, 0f, -12000f),
                    new Vector3(15000f, 0f, 12000f), new Vector3(-15000f, 0f, 12000f)
                };
                mesh.triangles = new[] { 0, 2, 1, 0, 3, 2 };
                mesh.RecalculateNormals();
                mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, meshPath);
            }
            var water = new GameObject("VictoriaHarbour_Water_PBR", typeof(MeshFilter), typeof(MeshRenderer));
            water.transform.SetParent(parent, false);
            water.transform.position = new Vector3(0f, -3.75f, 0f);
            water.GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = water.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            return water;
        }
    }
}
