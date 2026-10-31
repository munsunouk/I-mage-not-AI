using System;
using System.IO;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class i_mage_not_aiIntegrationProbe
{
    static i_mage_not_aiIntegrationProbe() { EditorApplication.delayCall += Run; }
    private static void Run()
    {
        try
        {
            var clip = new AnimationClip { name = "fixture_walk", frameRate = 30f };
            string[] axes = { "x", "y", "z" };
            float[][] positions = { new[] { 0f, 1f }, new[] { 0f, 2f }, new[] { 0f, 3f } };
            for (int i = 0; i < 3; i++) AnimationUtility.SetEditorCurve(clip, EditorCurveBinding.FloatCurve("Animated", typeof(Transform), "m_LocalPosition." + axes[i]), AnimationCurve.Linear(0f, positions[i][0], 1f, positions[i][1]));
            float[][] rotations = { new[] { 0f, 0f }, new[] { 0f, 0.3826834f }, new[] { 0f, 0f }, new[] { 1f, 0.9238795f } };
            string[] qaxes = { "x", "y", "z", "w" };
            for (int i = 0; i < 4; i++) AnimationUtility.SetEditorCurve(clip, EditorCurveBinding.FloatCurve("Animated", typeof(Transform), "m_LocalRotation." + qaxes[i]), AnimationCurve.Linear(0f, rotations[i][0], 1f, rotations[i][1]));
            for (int i = 0; i < 3; i++) AnimationUtility.SetEditorCurve(clip, EditorCurveBinding.FloatCurve("Animated", typeof(Transform), "m_LocalScale." + axes[i]), AnimationCurve.Linear(0f, 1f, 1f, i == 1 ? 2f : 1f));
            AnimationUtility.SetAnimationEvents(clip, new[] { new AnimationEvent { time = 0.5f, functionName = "fixture_marker" } });
            AssetDatabase.CreateAsset(clip, "Assets/fixture_walk.anim"); AssetDatabase.SaveAssets(); Selection.activeObject = clip;
            string output = Path.GetFullPath("i_mage_not_ai-unity-export.json");
            File.WriteAllText(output, i_mage_not_aiTraceExporter.BuildExport(clip));
            File.WriteAllText(Path.GetFullPath("i_mage_not_ai-unity-editor-menu.txt"), "Assets/Export AnimationClip as i_mage_not_ai Trace");
            Debug.Log("I_MAGE_NOT_AI_INTEGRATION_PASS Unity " + Application.unityVersion + " output=" + output);
        }
        catch (Exception ex) { File.WriteAllText(Path.GetFullPath("i_mage_not_ai-unity-integration-error.txt"), ex.ToString()); Debug.LogException(ex); }
    }
}
