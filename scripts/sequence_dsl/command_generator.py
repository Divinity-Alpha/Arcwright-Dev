"""Sequence DSL Command Generator — uses existing Batch 2 sequence commands."""
from typing import List

def _cmd(c, p): return {"command": c, "params": p}

def _parse_vec(s):
    parts = s.split(",")
    return {"x": float(parts[0]), "y": float(parts[1]) if len(parts)>1 else 0, "z": float(parts[2]) if len(parts)>2 else 0}

def generate(tree: dict) -> List[dict]:
    commands = []
    seq_name = tree["name"]
    props = tree.get("properties", {})
    duration = float(props.get("duration", "10"))

    # Create sequence (existing command)
    commands.append(_cmd("create_sequence", {"name": seq_name, "duration": duration}))

    # Cameras — add as transform tracks on a camera actor
    for cam in tree.get("cameras", []):
        cam_props = cam.get("properties", {})
        # Bind camera actor + add transform track
        commands.append(_cmd("add_sequence_camera", {
            "sequence": seq_name, "camera_name": cam["name"],
            "fov": float(cam_props.get("fov", "90")),
        }))
        # Add keyframes
        for kf in cam.get("keyframes", []):
            kfp = kf.get("properties", kf)
            value = {}
            if "location" in kfp: value["location"] = _parse_vec(kfp["location"])
            if "rotation" in kfp: value["rotation"] = _parse_vec(kfp["rotation"])
            if "fov" in kfp: value["fov"] = float(kfp["fov"])
            commands.append(_cmd("add_keyframe", {
                "sequence": seq_name, "track": cam["name"] + "_Transform",
                "time": kf["time"], "value": value,
            }))

    # Actors
    for actor in tree.get("actors", []):
        actor_props = actor.get("properties", {})
        binding = actor_props.get("binding", actor["name"])
        for track in actor.get("tracks", []):
            commands.append(_cmd("add_sequence_track", {
                "sequence": seq_name, "actor": binding, "track_type": track["name"],
            }))
            for kf in track.get("keyframes", []):
                kfp = kf.get("properties", kf)
                value = {}
                if "location" in kfp: value["location"] = _parse_vec(kfp["location"])
                if "rotation" in kfp: value["rotation"] = _parse_vec(kfp["rotation"])
                if "visible" in kfp: value["visible"] = kfp["visible"] == "true"
                commands.append(_cmd("add_keyframe", {
                    "sequence": seq_name, "track": f"{binding}_{track['name']}",
                    "time": kf["time"], "value": value,
                }))

    # Audio
    for audio in tree.get("audio", []):
        ap = audio.get("properties", {})
        commands.append(_cmd("add_sequence_audio", {
            "sequence": seq_name, "audio_name": audio["name"],
            "sound": ap.get("sound", ""), "start_time": float(ap.get("start_time", "0")),
            "volume": float(ap.get("volume", "1")), "fade_in": float(ap.get("fade_in", "0")),
        }))

    # Fades
    for fade in tree.get("fades", []):
        commands.append(_cmd("add_sequence_fade", {"sequence": seq_name}))
        for kf in fade.get("keyframes", []):
            kfp = kf.get("properties", kf)
            commands.append(_cmd("add_keyframe", {
                "sequence": seq_name, "track": "Fade",
                "time": kf["time"], "value": {"opacity": float(kfp.get("opacity", "1"))},
            }))

    # Events
    for event in tree.get("events", []):
        for action in event.get("actions", []):
            commands.append(_cmd("add_sequence_event", {
                "sequence": seq_name, "time": event["time"], "action": action.get("value", ""),
            }))

    return commands
