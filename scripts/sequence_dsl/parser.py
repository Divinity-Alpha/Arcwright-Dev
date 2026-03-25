"""Sequence DSL Parser."""
from typing import List
from .lexer import Token

def parse(tokens: List[Token]) -> dict:
    result = {"name": "LS_Untitled", "properties": {}, "cameras": [], "actors": [], "audio": [], "fades": [], "events": []}
    current = None  # current camera/actor/audio/fade
    current_track = None
    current_kf_target = None  # where keyframes attach

    for tok in tokens:
        if tok.type == "SEQUENCE":
            result["name"] = tok.name
        elif tok.type == "CAMERA":
            current = {"name": tok.name, "properties": {}, "keyframes": []}
            result["cameras"].append(current)
            current_track = None; current_kf_target = current
        elif tok.type == "ACTOR":
            current = {"name": tok.name, "properties": {}, "tracks": []}
            result["actors"].append(current)
            current_track = None; current_kf_target = None
        elif tok.type == "TRACK":
            current_track = {"name": tok.name, "keyframes": []}
            if current and "tracks" in current:
                current["tracks"].append(current_track)
            current_kf_target = current_track
        elif tok.type == "AUDIO":
            current = {"name": tok.name, "properties": {}}
            result["audio"].append(current)
            current_kf_target = None; current_track = None
        elif tok.type == "FADE":
            fade = {"keyframes": []}
            result["fades"].append(fade)
            current = fade; current_kf_target = fade; current_track = None
        elif tok.type == "EVENT":
            event = {"time": float(tok.value), "actions": []}
            result["events"].append(event)
            current = event; current_kf_target = None; current_track = None
        elif tok.type == "KEYFRAME":
            kf = {"time": float(tok.value), "properties": {}}
            if current_kf_target and "keyframes" in current_kf_target:
                current_kf_target["keyframes"].append(kf)
            current = kf  # properties attach to this keyframe
        elif tok.type == "PROPERTY":
            # Top-level properties first
            if tok.key in ("duration", "framerate", "autoplay") and tok.indent == 0:
                result["properties"][tok.key] = tok.value
            elif isinstance(current, dict):
                if "actions" in current and tok.key == "action":
                    current["actions"].append({"key": tok.key, "value": tok.value})
                elif "properties" in current:
                    current["properties"][tok.key] = tok.value
                else:
                    current[tok.key] = tok.value
    return result
