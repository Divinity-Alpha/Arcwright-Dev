"""Sound DSL Command Generator — converts parsed tree to real TCP sound commands."""

from typing import List


def _cmd(command: str, params: dict) -> dict:
    return {"command": command, "params": params}


def generate(tree: dict) -> List[dict]:
    """Convert a parsed Sound DSL tree into a sequence of TCP commands.

    Element type mapping:
      SOUND_CLASS  -> create_sound_class   (name, volume, pitch, parent_class)
      ATTENUATION  -> create_attenuation_settings (name, inner_radius, outer_radius, spatialization)
      REVERB_ZONE  -> create_audio_volume + set_reverb_settings (location, reverb_preset)
      AMBIENT      -> create_ambient_sound (sound_asset, location, auto_play, attenuation, label)
      SOUND_CUE    -> create_sound_cue (name, sounds, randomize)
      CONCURRENCY  -> set_sound_concurrency (name, max_count, resolution_rule)
    """
    commands = []

    for elem in tree.get("elements", []):
        etype = elem["type"].upper()
        name = elem["name"]
        props = elem.get("properties", {})

        if etype == "SOUND_CLASS":
            params = {"name": name}
            if "volume" in props:
                params["volume"] = float(props["volume"])
            if "pitch" in props:
                params["pitch"] = float(props["pitch"])
            if "parent_class" in props:
                params["parent_class"] = props["parent_class"]
            commands.append(_cmd("create_sound_class", params))

        elif etype == "ATTENUATION":
            params = {"name": name}
            if "inner_radius" in props:
                params["inner_radius"] = float(props["inner_radius"])
            if "outer_radius" in props or "falloff_distance" in props:
                params["outer_radius"] = float(props.get("outer_radius", props.get("falloff_distance", "2000")))
            if "spatialization" in props:
                params["spatialization"] = props["spatialization"].lower() in ("true", "1", "yes")
            commands.append(_cmd("create_attenuation_settings", params))

        elif etype == "REVERB_ZONE":
            vol_params = {}
            if "location" in props:
                parts = str(props["location"]).split(",")
                if len(parts) >= 3:
                    vol_params["location"] = {"x": float(parts[0]), "y": float(parts[1]), "z": float(parts[2])}
            reverb_preset = props.get("reverb_effect", props.get("reverb_preset", "None"))
            vol_params["reverb_preset"] = reverb_preset
            vol_params["label"] = name
            commands.append(_cmd("create_audio_volume", vol_params))

            # If there's a reverb effect, also set reverb settings explicitly
            if reverb_preset and reverb_preset != "None":
                rev_params = {"audio_volume": name, "preset": reverb_preset}
                if "volume" in props:
                    rev_params["volume"] = float(props["volume"])
                if "fade_time" in props:
                    rev_params["fade_time"] = float(props["fade_time"])
                commands.append(_cmd("set_reverb_settings", rev_params))

        elif etype == "AMBIENT":
            params = {}
            # sound_asset is required — mapped from @sound property
            sound = props.get("sound", props.get("sound_asset", ""))
            params["sound_asset"] = sound
            if "location" in props:
                parts = str(props["location"]).split(",")
                if len(parts) >= 3:
                    params["location"] = {"x": float(parts[0]), "y": float(parts[1]), "z": float(parts[2])}
            if "auto_play" in props:
                params["auto_play"] = props["auto_play"].lower() in ("true", "1", "yes")
            # @class or @attenuation maps to attenuation settings name
            att = props.get("attenuation", props.get("class", ""))
            if att:
                params["attenuation"] = att
            params["label"] = name
            commands.append(_cmd("create_ambient_sound", params))

        elif etype == "SOUND_CUE":
            params = {"name": name}
            if "sounds" in props:
                # Accept comma-separated list or already a list
                sounds = props["sounds"]
                if isinstance(sounds, str):
                    sounds = [s.strip() for s in sounds.split(",")]
                params["sounds"] = sounds
            if "randomize" in props:
                params["randomize"] = props["randomize"].lower() in ("true", "1", "yes")
            commands.append(_cmd("create_sound_cue", params))

        elif etype == "CONCURRENCY":
            params = {"name": name}
            if "max_count" in props:
                params["max_count"] = int(props["max_count"])
            if "resolution_rule" in props:
                params["resolution_rule"] = props["resolution_rule"]
            commands.append(_cmd("set_sound_concurrency", params))

        elif etype == "SOUND_MIX":
            params = {"name": name}
            if "modifiers" in props:
                params["modifiers"] = props["modifiers"]
            commands.append(_cmd("create_sound_mix", params))

        else:
            # Unknown element type — pass through as generic
            commands.append(_cmd("add_sound_element", {
                "config": tree.get("name", ""),
                "element_type": etype,
                "element_name": name,
                **props,
            }))

    return commands
