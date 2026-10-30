using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

public static class ImreviewIntegrationRunner
{
    public static void Run()
    {
        try
        {
            var menuMethod = typeof(ImreviewTraceExporter).GetMethod("ExportSelectedClip", BindingFlags.NonPublic | BindingFlags.Static);
            var menu = menuMethod == null ? null : (MenuItem)Attribute.GetCustomAttribute(menuMethod, typeof(MenuItem));
            if (menu == null || menu.menuItem != "Assets/Export AnimationClip as imreview Trace")
                throw new InvalidOperationException("Expected Unity Assets menu integration was not registered.");

            var clip = new AnimationClip { name = "fixture_walk", frameRate = 30f };
            string[] axes = { "x", "y", "z" };
            float[][] positions = { new[] { 0f, 1f }, new[] { 0f, 2f }, new[] { 0f, 3f } };
            for (int i = 0; i < 3; i++) AnimationUtility.SetEditorCurve(clip, EditorCurveBinding.FloatCurve("Animated", typeof(Transform), "m_LocalPosition." + axes[i]), AnimationCurve.Linear(0f, positions[i][0], 1f, positions[i][1]));
            float[][] rotations = { new[] { 0f, 0f }, new[] { 0f, 0.3826834f }, new[] { 0f, 0f }, new[] { 1f, 0.9238795f } };
            string[] qaxes = { "x", "y", "z", "w" };
            for (int i = 0; i < 4; i++) AnimationUtility.SetEditorCurve(clip, EditorCurveBinding.FloatCurve("Animated", typeof(Transform), "m_LocalRotation." + qaxes[i]), AnimationCurve.Linear(0f, rotations[i][0], 1f, rotations[i][1]));
            for (int i = 0; i < 3; i++) AnimationUtility.SetEditorCurve(clip, EditorCurveBinding.FloatCurve("Animated", typeof(Transform), "m_LocalScale." + axes[i]), AnimationCurve.Linear(0f, 1f, 1f, i == 1 ? 2f : 1f));
            AnimationUtility.SetAnimationEvents(clip, new[] { new AnimationEvent { time = 0.5f, functionName = "fixture_marker" } });
            const string clipPath = "Assets/fixture_walk.anim";
            if (AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath) != null) AssetDatabase.DeleteAsset(clipPath);
            AssetDatabase.CreateAsset(clip, clipPath);
            AssetDatabase.SaveAssets();
            var json = ImreviewTraceExporter.BuildExport(clip);
            if (!json.Contains("imreview.unity-export/1") || !json.Contains("fixture_marker") || !json.Contains("fixture_walk::Animated") || !json.Contains("fixture_walk::Animated::rotation") || !json.Contains("\"kind\":\"rotation\""))
                throw new InvalidOperationException("Unity trace output did not contain the expected version, position, rotation, and event data.");
            File.WriteAllText(Path.GetFullPath("imreview-unity-export.json"), json);
            File.WriteAllText(Path.GetFullPath("imreview-unity-editor-menu.txt"), menu.menuItem);
            Debug.Log("IMREVIEW_INTEGRATION_PASS Unity " + Application.unityVersion + " menu=" + menu.menuItem);
            EditorApplication.Exit(0);
        }
        catch (Exception ex)
        {
            File.WriteAllText(Path.GetFullPath("imreview-unity-integration-error.txt"), ex.ToString());
            Debug.LogException(ex);
            EditorApplication.Exit(1);
        }
    }
}
