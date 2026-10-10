using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace HKFlightDemo.Editor
{
    /// <summary>Reimport only HSBC, preserving the rest of the island and original recoverable renderers.</summary>
    public static class HsbcBuildingRepair
    {
        public const string AssetPath = "Assets/_FlightDemo/Art/World/HSBC/HSBC_MainBuilding_Opaque.glb";
        public const string ReplacementName = "HSBC_MainBuilding_Reimported";
        private static readonly string[] OriginalNames = {
            "B344751569101063A1_Standardmaterial_0", "B344751569101063A1_Standardmaterial_0.001"
        };
        private static readonly int[] TriangleCounts = { 26653, 1091 };

        [MenuItem("Tools/HK Flight Demo/Repair HSBC Building")]
        public static void ApplyMenu() { Debug.Log(Apply()); }

        public static string Apply()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("Stop Play Mode before repairing HSBC.");
            if (SceneManager.GetActiveScene().path != "Assets/_FlightDemo/Scenes/HKFlight_Demo.unity")
                throw new InvalidOperationException("Open HKFlight_Demo first.");
            var world = GameObject.Find("World_HongKongIsland_PBR");
            if (world == null) throw new InvalidOperationException("Island root missing.");
            var originals = OriginalNames.Select(n => world.GetComponentsInChildren<MeshRenderer>(true).Single(r => r.name == n)).ToArray();
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(AssetPath);
            if (asset == null) throw new InvalidOperationException("Import the extracted HSBC GLB first.");
            Transform existing = world.transform.Find(ReplacementName);
            GameObject replacement = existing != null ? existing.gameObject : null;
            bool created = replacement == null;
            int group = Undo.GetCurrentGroup();
            Undo.SetCurrentGroupName("Reimport complete opaque HSBC building");
            try
            {
                if (created)
                {
                    replacement = (GameObject)PrefabUtility.InstantiatePrefab(asset, world.transform);
                    Undo.RegisterCreatedObjectUndo(replacement, "Import HSBC from Blender");
                    replacement.name = ReplacementName;
                    replacement.transform.localPosition = Vector3.zero;
                    replacement.transform.localRotation = Quaternion.identity;
                    replacement.transform.localScale = Vector3.one;
                }
                // Validate every part before hiding any original geometry. No arbitrary rescaling or repositioning.
                Validate(replacement, originals);
                for (int i = 0; i < originals.Length; i++)
                {
                    Undo.RecordObject(originals[i], "Hide superseded transparent HSBC facade");
                    originals[i].enabled = false;
                    PrefabUtility.RecordPrefabInstancePropertyModifications(originals[i]);
                    EditorUtility.SetDirty(originals[i]);
                }
                PrefabUtility.RecordPrefabInstancePropertyModifications(replacement.transform);
                EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
                EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
                Undo.CollapseUndoOperations(group);
                return Check();
            }
            catch
            {
                Undo.RevertAllDownToGroup(group);
                throw;
            }
        }

        private static void Validate(GameObject replacement, MeshRenderer[] originals)
        {
            var parts = replacement.GetComponentsInChildren<MeshRenderer>(true).OrderBy(r => r.name).ToArray();
            if (parts.Length != 2) throw new InvalidOperationException("HSBC must contain both original facade parts.");
            for (int i = 0; i < parts.Length; i++)
            {
                var mesh = parts[i].GetComponent<MeshFilter>().sharedMesh;
                if (mesh.triangles.Length / 3 != TriangleCounts[i] || mesh.uv.Length != mesh.vertexCount)
                    throw new InvalidOperationException("HSBC geometry or UV count mismatch.");
                if ((parts[i].bounds.center - originals[i].bounds.center).magnitude > .02f ||
                    (parts[i].bounds.size - originals[i].bounds.size).magnitude > .04f)
                    throw new InvalidOperationException("HSBC world alignment differs from original by more than Draco tolerance.");
                foreach (var m in parts[i].sharedMaterials)
                {
                    if (m == null || !m.shader.isSupported || m.renderQueue != 2000 ||
                        !m.HasProperty("_Surface") || m.GetFloat("_Surface") != 0f ||
                        !m.HasProperty("_ZWrite") || m.GetFloat("_ZWrite") != 1f ||
                        m.GetTexture("baseColorTexture") == null || m.GetColor("baseColorFactor").a != 1f ||
                        (m.HasProperty("transmissionFactor") && m.GetFloat("transmissionFactor") != 0f))
                        throw new InvalidOperationException("HSBC facade must be textured, opaque, depth-writing and non-transmissive.");
                }
                if (!parts[i].enabled || !parts[i].gameObject.activeInHierarchy)
                    throw new InvalidOperationException("Replacement HSBC facade is not visible.");
            }
        }

        public static string Check()
        {
            var world = GameObject.Find("World_HongKongIsland_PBR");
            var replacement = world.transform.Find(ReplacementName).gameObject;
            var originals = OriginalNames.Select(n => world.GetComponentsInChildren<MeshRenderer>(true).Single(r => r.name == n)).ToArray();
            Validate(replacement, originals);
            if (originals.Any(r => r.enabled)) throw new InvalidOperationException("Old and new HSBC facades overlap.");
            return Newtonsoft.Json.JsonConvert.SerializeObject(new {
                asset = AssetPath, originalRenderersDisabled = originals.Length,
                parts = replacement.GetComponentsInChildren<MeshRenderer>(true).OrderBy(r => r.name).Select((r, i) => new {
                    name = r.name, triangles = r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3,
                    bounds = r.bounds.ToString(), centerErrorMeters = (r.bounds.center - originals[i].bounds.center).magnitude,
                    opaque = r.sharedMaterial.GetFloat("_Surface") == 0f, depthWrite = r.sharedMaterial.GetFloat("_ZWrite") == 1f,
                    textureSize = r.sharedMaterial.GetTexture("baseColorTexture").width
                }).ToArray()
            });
        }
    }
}
