using System;
using System.Collections;
using System.IO;
using UnityEngine;

public sealed class ImreviewRuntimeWaiter : MonoBehaviour
{
    public static bool Completed { get; private set; }
    public static string Failure { get; private set; }
    private ImreviewRuntimeCallback callback;
    private ParticleSystem system;
    private GameObject callbackObject;
    private GameObject particleObject;
    private string controllerPath;
    private int seed;

    public void Begin(ImreviewRuntimeCallback observedCallback, ParticleSystem observedSystem, GameObject observedCallbackObject, GameObject observedParticleObject, string generatedControllerPath, int randomSeed)
    {
        callback = observedCallback;
        system = observedSystem;
        callbackObject = observedCallbackObject;
        particleObject = observedParticleObject;
        controllerPath = generatedControllerPath;
        seed = randomSeed;
        Completed = false;
        Failure = null;
        StartCoroutine(Capture());
    }

    private IEnumerator Capture()
    {
        for (var frame = 0; frame < 16; frame++) yield return null;
        try
        {
            var particles = new ParticleSystem.Particle[16];
            var alive = system.GetParticles(particles);
            if (callback.CallbackTimes.Count != 1 || Mathf.Abs(callback.CallbackTimes[0] - 0.5f) > 1e-5f)
                throw new InvalidOperationException("Expected one runtime callback at 0.5 seconds; observed " + callback.CallbackTimes.Count + ".");
            if (alive != 8) throw new InvalidOperationException("Expected 8 live particles after 0.25 seconds; observed " + alive + ".");
            var minX = float.PositiveInfinity; var maxX = float.NegativeInfinity;
            var minZ = float.PositiveInfinity; var maxZ = float.NegativeInfinity; var maxAbsY = 0f;
            for (var index = 0; index < alive; index++)
            {
                var position = particles[index].position;
                minX = Mathf.Min(minX, position.x); maxX = Mathf.Max(maxX, position.x);
                minZ = Mathf.Min(minZ, position.z); maxZ = Mathf.Max(maxZ, position.z);
                maxAbsY = Mathf.Max(maxAbsY, Mathf.Abs(position.y));
            }
            Debug.Log("IMREVIEW_RUNTIME_PARTICLES count=" + alive + " x=" + minX + ".." + maxX + " z=" + minZ + ".." + maxZ + " maxAbsY=" + maxAbsY);
            if (minX < -0.0002f || maxX > 0.0002f || minZ < 0.45f || maxZ > 0.55f || maxAbsY > 0.0002f)
                throw new InvalidOperationException("Live particle positions outside deterministic local XZ bounds: x=" + minX + ".." + maxX + " z=" + minZ + ".." + maxZ + " maxAbsY=" + maxAbsY);
            var evidence = "{\"format\":\"imreview.runtime-evidence/1\",\"engine\":\"unity\",\"engine_version\":\"" + Application.unityVersion +
                "\",\"timebase\":\"seconds\",\"random_seed\":" + seed +
                ",\"callbacks\":[{\"name\":\"FixtureMarker\",\"time\":" + callback.CallbackTimes[0].ToString("R", System.Globalization.CultureInfo.InvariantCulture) +
                "}],\"particles\":[{\"emitter\":\"RuntimeParticles\",\"sample_time\":" + system.time.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + ",\"alive_count\":" + alive +
                ",\"bounds\":[" + minX.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + "," + minZ.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + "," + maxX.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + "," + maxZ.ToString("R", System.Globalization.CultureInfo.InvariantCulture) +
                "],\"bounds_units\":\"local_xz_engine_unit\"}],\"checks\":{\"callback_exactly_once_at_half_second\":true,\"particle_count_is_eight\":true,\"particle_positions_within_fixture_bounds\":true}}";
            File.WriteAllText(Path.GetFullPath("imreview-unity-runtime-evidence.json"), evidence);
            Debug.Log("IMREVIEW_RUNTIME_PASS Unity callback=1 particles=" + alive);
            UnityEngine.Object.Destroy(particleObject); UnityEngine.Object.Destroy(callbackObject); Destroy(gameObject);
        }
        catch (Exception exception) { Failure = exception.ToString(); Debug.LogException(exception); }
        finally { Time.captureDeltaTime = 0f; Completed = true; }
    }
}
