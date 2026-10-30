# Game asset extension roadmap

Canonical JSON traces are integrated with manifest validation, capability planning, reports, and coverage. The reader also accepts versioned Godot 4 and Unity export wrappers around the same canonical trace. It never opens engine project files or runs project scripts.

Trace evidence includes frame sequences, position/rotation/pose tracks, events, contact intervals, anchor pairs, particles, and PNG frame layers. Samples declare timebase, frame/timestamp, coordinate space, units, interpolation, and random seed where relevant.

Implemented checks include position, velocity, acceleration, jerk, quaternion rotation distance, pose and loop boundaries, event timing, anchor distance, bone-length deviation, foot sliding, particle lifetime and AABB bounds, and alpha-weighted occlusion. Layer records can select `[x, y, width, height]` regions from sprite atlases. Local positions compose through synchronized parent tracks with per-sample 2D/3D basis matrices, including changing rotation and scale. Paths stay within the trace directory. Missing or incompatible evidence yields `INCONCLUSIVE`.

Remaining game work: editor-side exporters and fixtures produced by supported Godot/Unity releases. The CLI keeps plugin loading disabled; embedding hosts can use the documented API only for explicitly reviewed code.
