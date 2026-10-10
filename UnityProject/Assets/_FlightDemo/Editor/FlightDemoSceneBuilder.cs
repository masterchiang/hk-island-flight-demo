using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace HKFlightDemo.Editor
{
    /// <summary>One-off authoring helper. Never overwrites an existing demo scene.</summary>
    public static class FlightDemoSceneBuilder
    {
        public const string Root = "Assets/_FlightDemo";
        public const string ScenePath = Root + "/Scenes/HKFlight_Demo.unity";

        [MenuItem("Tools/HK Flight Demo/1 - Create Placeholder Scene")]
        public static void CreateScene()
        {
            if (Application.isPlaying) throw new InvalidOperationException("Stop Play Mode first.");
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath) != null)
                throw new InvalidOperationException("Demo scene already exists. Open it; do not overwrite authored content.");
            if (SceneManager.GetActiveScene().isDirty)
                throw new InvalidOperationException("Current scene has unsaved edits. Save it before creating the demo.");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var world = new GameObject("World_Placeholder_ReplaceWithHKIsland").transform;
            var aircraft = new GameObject("AircraftRoot").transform;
            var visual = new GameObject("Visual_ReplaceWithJ20").transform;
            visual.SetParent(aircraft, false);
            new GameObject("Systems");
            new GameObject("Route");
            new GameObject("Safety");

            var water = Material("Water", new Color(.055f,.23f,.28f), .55f, .25f);
            var shore = Material("Shore", new Color(.34f,.49f,.42f), .05f, .1f);
            var hill = Material("Hills", new Color(.12f,.28f,.23f), 0, .1f);
            var city = Material("City", new Color(.65f,.72f,.71f), .3f, .4f);
            var glass = Material("Glass", new Color(.17f,.31f,.36f), .6f, .65f);
            var plane = Material("Aircraft", new Color(.45f,.54f,.58f), .7f, .5f);
            var dark = Material("Canopy", new Color(.035f,.075f,.10f), .6f, .85f);
            var engine = Material("Engine", new Color(.08f,.1f,.11f), .6f, .35f);
            var accent = Material("Accent", new Color(.18f,.8f,.82f), .4f, .45f);
            Primitive("Sea", PrimitiveType.Cube, world, new Vector3(0,-10,0), new Vector3(16000,20,16000), water);
            Primitive("IslandBase", PrimitiveType.Sphere, world, new Vector3(0,3,0), new Vector3(2170,100,1000), shore);
            for (int i=0;i<6;i++)
            {
                float x=-700+i*270;
                Primitive("Hill_"+i, PrimitiveType.Sphere, world, new Vector3(x,48,-80+40*Mathf.Sin(i)),
                    new Vector3(470,210+70*Mathf.Sin(i*.8f),390), hill);
            }
            var rng = new System.Random(2040);
            for (int i=0;i<66;i++)
            {
                float x=-830+(i%22)*78;
                float z=230+(i/22)*70;
                float h=35+(float)rng.NextDouble()*125;
                Primitive("Building_"+i.ToString("00"), PrimitiveType.Cube, world, new Vector3(x,30+h*.5f,z),
                    new Vector3(24+(float)rng.NextDouble()*18,h,25+(float)rng.NextDouble()*15), i%4==0?glass:city);
            }
            Primitive("FeatureTower", PrimitiveType.Cube, world, new Vector3(-150,165,340), new Vector3(45,290,40), glass);
            Primitive("FeatureTowerCrown", PrimitiveType.Cube, world, new Vector3(-150,320,340), new Vector3(25,24,24), city);
            Primitive("HarbourDeck", PrimitiveType.Cube, world, new Vector3(100,15,445), new Vector3(1150,24,65), city);
            // Deliberately a generic jet proxy, not a claimed accurate J-20 model.
            var hull = new Vector3[] {
                new Vector3(0,0,11), new Vector3(-1.4f,0,5), new Vector3(-2,0,-7), new Vector3(0,0,-9), new Vector3(2,0,-7), new Vector3(1.4f,0,5),
                new Vector3(0,1,5),new Vector3(0,1.2f,-5),new Vector3(0,-.9f,-4)
            };
            MeshPart("Fuselage", visual, hull, new int[]{0,6,1,0,5,6,1,6,7,1,7,2,5,4,7,5,7,6,2,7,3,3,7,4,0,1,8,0,8,5,1,2,8,2,3,8,3,4,8,4,5,8}, plane);
            Polygon("DeltaWings", visual, new Vector3[]{new Vector3(-1,0,3),new Vector3(-7.5f,-.1f,-5),new Vector3(-2,-.1f,-6),new Vector3(2,-.1f,-6),new Vector3(7.5f,-.1f,-5),new Vector3(1,0,3)}, plane);
            Polygon("Canards", visual, new Vector3[]{new Vector3(-1,0,6),new Vector3(-4.1f,0,3.1f),new Vector3(-1,0,3.8f),new Vector3(1,0,3.8f),new Vector3(4.1f,0,3.1f),new Vector3(1,0,6)}, plane);
            for(int s=-1;s<=1;s+=2)
            {
                Polygon("TailFin_"+s, visual, new Vector3[]{new Vector3(s*1.5f,.5f,-3),new Vector3(s*2.9f,3.3f,-5.5f),new Vector3(s*2.3f,.5f,-8)}, plane);
                var nozzle=Primitive("Engine_"+s, PrimitiveType.Cylinder, visual,new Vector3(s*1.1f,0,-7.2f),new Vector3(1.5f,1.35f,1.5f),engine);
                nozzle.localRotation=Quaternion.Euler(90,0,0);
                Primitive("WingLight_"+s,PrimitiveType.Sphere,visual,new Vector3(s*7.2f,0,-4.9f),Vector3.one*.25f,accent);
            }
            Primitive("Canopy",PrimitiveType.Sphere,visual,new Vector3(0,1,4),new Vector3(1.8f,1.4f,4.8f),dark);
            aircraft.position=new Vector3(0,350,-1150);
            aircraft.rotation=Quaternion.Euler(0,90,0);
            var rb=aircraft.gameObject.AddComponent<Rigidbody>();
            rb.isKinematic=true; rb.useGravity=false; rb.interpolation=RigidbodyInterpolation.Interpolate;
            var cameraGo=new GameObject("Main Camera",typeof(Camera),typeof(AudioListener));
            cameraGo.tag="MainCamera";
            var camera=cameraGo.GetComponent<Camera>();
            camera.nearClipPlane=.5f; camera.farClipPlane=16000; camera.fieldOfView=55;
            camera.clearFlags=CameraClearFlags.Skybox;
            camera.transform.position=new Vector3(0,1350,-2400);
            camera.transform.LookAt(new Vector3(0,80,0));
            var sun=new GameObject("Sun",typeof(Light)).GetComponent<Light>();
            sun.type=LightType.Directional; sun.intensity=2; sun.color=new Color(1,.93f,.83f);
            sun.shadows=LightShadows.Soft; sun.transform.rotation=Quaternion.Euler(38,-35,0);
            RenderSettings.sun=sun;
            RenderSettings.ambientMode=AmbientMode.Trilight;
            RenderSettings.ambientSkyColor=new Color(.43f,.61f,.7f);
            RenderSettings.ambientEquatorColor=new Color(.32f,.42f,.45f);
            RenderSettings.ambientGroundColor=new Color(.18f,.23f,.22f);
            RenderSettings.fog=true; RenderSettings.fogMode=FogMode.Linear;
            RenderSettings.fogColor=new Color(.45f,.63f,.69f); RenderSettings.fogStartDistance=2800; RenderSettings.fogEndDistance=11500;
            var sky=new Material(Shader.Find("Skybox/Procedural"));
            sky.SetColor("_SkyTint",new Color(.43f,.61f,.73f)); sky.SetFloat("_AtmosphereThickness",.8f);
            AssetDatabase.CreateAsset(sky,Root+"/Materials/Sky.mat"); RenderSettings.skybox=sky;
            AssetDatabase.SaveAssets();
            EditorSceneManager.SaveScene(scene,ScenePath);
            if(SceneView.lastActiveSceneView!=null) SceneView.lastActiveSceneView.LookAt(new Vector3(0,100,0),Quaternion.Euler(30,0,0),2500);
            Debug.Log("[HKFlight] Step 1: placeholder scene created. No source map/model was imported or overwritten.");
        }

        private static Material Material(string name,Color color,float metal,float smooth)
        {
            string path=Root+"/Materials/"+name+".mat";
            var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(m!=null)return m;
            m=new Material(Shader.Find("Universal Render Pipeline/Lit")); m.name=name;
            m.SetColor("_BaseColor",color); m.SetFloat("_Metallic",metal); m.SetFloat("_Smoothness",smooth);
            AssetDatabase.CreateAsset(m,path); return m;
        }
        private static Transform Primitive(string name,PrimitiveType type,Transform parent,Vector3 p,Vector3 s,Material m)
        {
            var g=GameObject.CreatePrimitive(type); g.name=name; g.transform.SetParent(parent,false);
            g.transform.localPosition=p;g.transform.localScale=s;g.GetComponent<Renderer>().sharedMaterial=m;
            UnityEngine.Object.DestroyImmediate(g.GetComponent<Collider>());return g.transform;
        }
        private static void Polygon(string name,Transform parent,Vector3[] vertices,Material material)
        {
            var indices=new List<int>();for(int i=1;i<vertices.Length-1;i++){indices.Add(0);indices.Add(i);indices.Add(i+1);indices.Add(0);indices.Add(i+1);indices.Add(i);}
            MeshPart(name,parent,vertices,indices.ToArray(),material);
        }
        private static void MeshPart(string name,Transform parent,Vector3[] vertices,int[] triangles,Material material)
        {
            var mesh=new Mesh{name=name};mesh.vertices=vertices;mesh.triangles=triangles;mesh.RecalculateNormals();mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh,Root+"/Meshes/"+name+".asset");
            var go=new GameObject(name,typeof(MeshFilter),typeof(MeshRenderer));go.transform.SetParent(parent,false);
            go.GetComponent<MeshFilter>().sharedMesh=mesh;go.GetComponent<MeshRenderer>().sharedMaterial=material;
        }
    }
}
