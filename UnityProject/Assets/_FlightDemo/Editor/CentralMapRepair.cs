using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace HKFlightDemo.Editor
{
    public static class CentralMapRepair
    {
        private const string Folder = "Assets/_FlightDemo/Art/World/CentralRepairs";
        [MenuItem("Tools/HK Flight Demo/Repair Underground Station Artifacts")]
        public static string Apply()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Stop Play Mode first.");
            if (SceneManager.GetActiveScene().path != "Assets/_FlightDemo/Scenes/HKFlight_Demo.unity") throw new InvalidOperationException("Open demo scene first.");
            var world = GameObject.Find("World_HongKongIsland_PBR");
            if (world == null) throw new InvalidOperationException("World missing.");
            var plan = JObject.Parse(File.ReadAllText("Assets/_FlightDemo/Editor/RepairData/central_roof_repair_plan.json"));
            Directory.CreateDirectory(Folder);
            var report = new List<object>();
            foreach (var entry in plan["meshes"])
            {
                string name = (string)entry["name"];
                var filter = world.GetComponentsInChildren<MeshFilter>(true).Single(f => f.name == name);
                string path = Folder + "/" + name + "_Fixed.asset";
                var saved = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                if (saved != null)
                {
                    Undo.RecordObject(filter, "Reuse fixed underground station geometry");
                    filter.sharedMesh = saved;
                    PrefabUtility.RecordPrefabInstancePropertyModifications(filter);
                    EditorUtility.SetDirty(filter);
                    report.Add(new { name, alreadyPatched = true });
                    continue;
                }
                var source = filter.sharedMesh;
                var points = entry["vertices"].Select(p => new Vector3(-(float)p[0], (float)p[2], -(float)p[1])).ToArray();
                var vertices = source.vertices;
                bool[] marked = new bool[vertices.Length];
                // Draco position error measured < 0.011m. 0.015m does not conflate the roof and 0.1m inset LOD.
                const float tolerance = .015f;
                for (int i = 0; i < vertices.Length; i++)
                {
                    Vector3 v = vertices[i];
                    if (v.x < 7000 || v.x > 8400 || v.z < -1650 || v.z > -1000) continue;
                    marked[i] = points.Any(p => (p - v).sqrMagnitude <= tolerance * tolerance);
                }
                var replacement = UnityEngine.Object.Instantiate(source);
                replacement.name = name + "_UndergroundStationsFixed";
                int removed = 0;
                for (int s = 0; s < source.subMeshCount; s++)
                {
                    int[] indices = source.GetTriangles(s);
                    var keep = new List<int>(indices.Length);
                    for (int i = 0; i < indices.Length; i += 3)
                    {
                        if (marked[indices[i]] && marked[indices[i + 1]] && marked[indices[i + 2]]) { removed++; continue; }
                        keep.Add(indices[i]); keep.Add(indices[i + 1]); keep.Add(indices[i + 2]);
                    }
                    replacement.SetTriangles(keep, s, false);
                }
                int expected = name == "HKI_RF_Shells" ? 164 : 184;
                if (removed != expected) { UnityEngine.Object.DestroyImmediate(replacement); throw new InvalidOperationException(name + ": removed " + removed + " triangles, expected " + expected + ". No assignment made."); }
                AssetDatabase.CreateAsset(replacement, path);
                Undo.RecordObject(filter, "Fix underground station geometry");
                filter.sharedMesh = replacement;
                PrefabUtility.RecordPrefabInstancePropertyModifications(filter);
                EditorUtility.SetDirty(filter);
                report.Add(new { name, removedTriangles = removed, preservedVertices = replacement.vertexCount, preservedSubmeshes = replacement.subMeshCount });
            }
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
            return Newtonsoft.Json.JsonConvert.SerializeObject(report);
        }
    }
}
