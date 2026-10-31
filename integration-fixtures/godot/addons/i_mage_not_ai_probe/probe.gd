@tool
extends EditorPlugin

func _enter_tree() -> void:
	call_deferred("_run_probe")

func _run_probe() -> void:
	var scene_root := Node3D.new()
	scene_root.name = "Root"
	var animated := Node3D.new()
	animated.name = "Animated"
	scene_root.add_child(animated)
	animated.owner = scene_root
	var player := AnimationPlayer.new()
	player.name = "AnimationPlayer"
	scene_root.add_child(player)
	player.owner = scene_root

	var animation := Animation.new()
	animation.resource_name = "walk"
	animation.length = 1.0
	var position_track := animation.add_track(Animation.TYPE_POSITION_3D)
	animation.track_set_path(position_track, NodePath("Animated"))
	animation.track_insert_key(position_track, 0.0, Vector3.ZERO)
	animation.track_insert_key(position_track, 1.0, Vector3(1, 2, 3))
	var rotation_track := animation.add_track(Animation.TYPE_ROTATION_3D)
	animation.track_set_path(rotation_track, NodePath("Animated"))
	animation.track_insert_key(rotation_track, 0.0, Quaternion.IDENTITY)
	animation.track_insert_key(rotation_track, 1.0, Quaternion(Vector3.UP, PI / 4.0))
	var method_track := animation.add_track(Animation.TYPE_METHOD)
	animation.track_set_path(method_track, NodePath("."))
	animation.track_insert_key(method_track, 0.5, {"method": "fixture_marker", "args": []})
	var library := AnimationLibrary.new()
	library.add_animation("walk", animation)
	player.add_animation_library("", library)

	var packed_scene := PackedScene.new()
	var pack_error := packed_scene.pack(scene_root)
	if pack_error != OK:
		_fail("Could not pack fixture scene: %s" % error_string(pack_error))
		return
	var save_error := ResourceSaver.save(packed_scene, "res://test_scene.tscn")
	if save_error != OK:
		_fail("Could not save fixture scene: %s" % error_string(save_error))
		return
	scene_root.free()
	EditorInterface.open_scene_from_path("res://test_scene.tscn")

	var script_resource: Script = load("res://i_mage_not_ai_export.gd")
	if script_resource == null or not script_resource.can_instantiate():
		_fail("Exporter script failed to load")
		return
	var exporter = script_resource.new()
	exporter._run()
	var output_path := "res://i_mage_not_ai-godot-export.json"
	if not FileAccess.file_exists(output_path):
		_fail("Exporter did not write its output")
		return
	var parsed := JSON.parse_string(FileAccess.get_file_as_string(output_path))
	if typeof(parsed) != TYPE_DICTIONARY:
		_fail("Exporter output is not JSON object")
		return
	if parsed.get("format", "") != "i_mage_not_ai.godot-export/1":
		_fail("Wrong export format: %s" % parsed.get("format", ""))
		return
	var trace: Dictionary = parsed.get("trace", {})
	var tracks: Array = trace.get("tracks", [])
	var events: Array = trace.get("events", [])
	var position_track_data: Dictionary = {}
	var rotation_track_data: Dictionary = {}
	for track in tracks:
		if track.get("kind", "") == "position":
			position_track_data = track
		elif track.get("kind", "") == "rotation":
			rotation_track_data = track
	if position_track_data.get("samples", []).size() != 2 or rotation_track_data.get("samples", []).size() != 2 or events.size() != 1:
		_fail("Expected two position samples, two rotation samples, and one event; got %d position samples, %d rotation samples, %d events" % [position_track_data.get("samples", []).size(), rotation_track_data.get("samples", []).size(), events.size()])
		return
	var marker := FileAccess.open("res://integration-result.txt", FileAccess.WRITE)
	marker.store_string("PASS Godot %s tracks=%d events=%d" % [parsed.get("engine_version", ""), tracks.size(), events.size()])
	marker.close()
	print("I_MAGE_NOT_AI_INTEGRATION_PASS Godot %s tracks=%d events=%d" % [parsed.get("engine_version", ""), tracks.size(), events.size()])

func _fail(message: String) -> void:
	var marker := FileAccess.open("res://integration-result.txt", FileAccess.WRITE)
	marker.store_string("FAIL " + message)
	marker.close()
	push_error("I_MAGE_NOT_AI_INTEGRATION_FAIL " + message)
