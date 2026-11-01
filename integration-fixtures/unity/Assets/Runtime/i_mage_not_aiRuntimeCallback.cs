using System.Collections.Generic;
using UnityEngine;

public sealed class i_mage_not_aiRuntimeCallback : MonoBehaviour
{
    public readonly List<float> CallbackTimes = new List<float>();

    public void FixtureMarker(AnimationEvent animationEvent)
    {
        var animator = GetComponent<Animator>();
        CallbackTimes.Add(animator.GetCurrentAnimatorStateInfo(0).normalizedTime);
    }
}
