extends Node2D

const SEED := 481516
const OUTPUT := "res://runtime-evidence.json"
var callbacks: Array[Dictionary] = []

func _ready() -> void:
	call_deferred("_run")

func fixture_marker() -> void:
	var player := get_node("AnimationPlayer") as AnimationPlayer
	callbacks.append({"name": "fixture_marker", "time": player.current_animation_position})

func _run() -> void:
	var player := AnimationPlayer.new()
	player.name = "AnimationPlayer"
	player.root_node = NodePath("..")
	add_child(player)
	var animation := Animation.new()
	animation.length = 1.0
	var method_track := animation.add_track(Animation.TYPE_METHOD)
	animation.track_set_path(method_track, NodePath("."))
	animation.track_insert_key(method_track, 0.5, {"method": "fixture_marker", "args": []})
	var library := AnimationLibrary.new()
	library.add_animation("runtime", animation)
	player.add_animation_library("", library)
	player.play("runtime")
	player.advance(0.5)

	var particles := GPUParticles2D.new()
	particles.name = "RuntimeParticles"
	particles.amount = 24
	particles.lifetime = 1.0
	particles.one_shot = true
	particles.explosiveness = 1.0
	particles.use_fixed_seed = true
	particles.seed = SEED
	particles.fixed_fps = 60
	particles.visibility_rect = Rect2(-10, -10, 150, 30)
	var material := ParticleProcessMaterial.new()
	material.direction = Vector3.RIGHT
	material.spread = 0.0
	material.initial_velocity_min = 80.0
	material.initial_velocity_max = 80.0
	material.gravity = Vector3.ZERO
	particles.process_material = material
	add_child(particles)
	particles.restart()
	for i in range(60):
		await get_tree().process_frame
	var captured: Rect2 = particles.capture_rect()
	var callback_ok: bool = callbacks.size() == 1
	var particle_ok: bool = captured.has_area() and captured.position.x >= 70.0 and captured.position.x <= 85.0 and captured.end.x >= captured.position.x and captured.end.x <= 90.0 and absf(captured.position.y) <= 2.0 and absf(captured.end.y) <= 2.0
	var result := {
		"format": "imreview.runtime-evidence/1", "engine": "godot",
		"engine_version": Engine.get_version_info().string, "timebase": "seconds", "random_seed": SEED,
		"callbacks": callbacks,
		"particles": [{"emitter": "RuntimeParticles", "sample_time": 1.0,
			"configured_capacity": particles.amount,
			"bounds": [captured.position.x, captured.position.y, captured.end.x, captured.end.y],
			"bounds_units": "engine_unit"}],
		"checks": {"callback_exactly_once_at_half_second": callback_ok,
			"particle_capture_within_fixture_bounds": particle_ok}
	}
	var file := FileAccess.open(OUTPUT, FileAccess.WRITE)
	if file == null:
		push_error("Could not write runtime evidence")
		get_tree().quit(1)
		return
	file.store_string(JSON.stringify(result, "\t"))
	file.close()
	if not callback_ok or not particle_ok:
		push_error("Runtime fixture failed: %s" % JSON.stringify(result))
		get_tree().quit(1)
		return
	print("IMREVIEW_RUNTIME_PASS Godot callbacks=1 particles_bounds=%s" % str(result.particles[0].bounds))
	get_tree().quit(0)
