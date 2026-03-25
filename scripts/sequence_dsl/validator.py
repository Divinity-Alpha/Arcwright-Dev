"""Sequence DSL Validator."""
from typing import List, Dict

def validate(tree: dict) -> Dict[str, List[str]]:
    errors, warnings = [], []
    duration = float(tree.get("properties", {}).get("duration", "0"))
    if duration <= 0: warnings.append("No @duration set on sequence")

    # Check keyframe times within duration
    if duration > 0:
        for cam in tree.get("cameras", []):
            for kf in cam.get("keyframes", []):
                if kf["time"] > duration:
                    errors.append(f"Camera '{cam['name']}' keyframe at {kf['time']}s exceeds duration {duration}s")
        for actor in tree.get("actors", []):
            for track in actor.get("tracks", []):
                for kf in track.get("keyframes", []):
                    if kf["time"] > duration:
                        errors.append(f"Actor '{actor['name']}' track '{track['name']}' keyframe at {kf['time']}s exceeds duration")
        for fade in tree.get("fades", []):
            for kf in fade.get("keyframes", []):
                if kf["time"] > duration:
                    errors.append(f"Fade keyframe at {kf['time']}s exceeds duration")
        for event in tree.get("events", []):
            if event["time"] > duration:
                errors.append(f"Event at {event['time']}s exceeds duration")

    if not tree.get("cameras") and not tree.get("actors"):
        warnings.append("Sequence has no cameras or actors")
    return {"errors": errors, "warnings": warnings}
