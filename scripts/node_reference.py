"""
Arcwright Node Reference — complete catalog of Blueprint node types.

Provides get_reference(node_type) and list_types() for AI assistants
to discover available nodes, their pins, and usage guidance.

Source of truth: scripts/dsl_parser/node_map.py (pin data)
This file adds: categories, descriptions, pin descriptions.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsl_parser.node_map import NODE_MAP, ALIASES, resolve

# ── Category assignments ──────────────────────────────────────────

_CAT = {}

def _assign(cat, names):
    for n in names:
        _CAT[n] = cat

_assign("Events", [
    "Event_BeginPlay", "Event_Tick", "Event_EndPlay",
    "Event_ActorBeginOverlap", "Event_ActorEndOverlap", "Event_EndOverlap",
    "Event_AnyDamage", "Event_Hit", "Event_InputAction",
    "Event_CustomEvent", "Event_Custom", "Event_Unknown",
    "Event_Overlap", "Event_OverlapActor",
])
_assign("Flow Control", [
    "Branch", "Sequence", "FlipFlop", "DoOnce", "Gate", "MultiGate",
])
_assign("Loops", [
    "ForLoop", "ForEachLoop", "WhileLoop",
])
_assign("Casting", [
    "CastToCharacter", "CastToPawn", "CastToPlayerController",
])
_assign("Variables", [
    "VariableGet", "GetVar", "VariableSet", "SetVar",
    "GetVariable", "SetVariable", "SetHealth", "VectorVariable",
])
_assign("Switch", [
    "SwitchOnInt", "SwitchOnString",
])
_assign("Debug", [
    "PrintString", "Print", "PrintFloat",
])
_assign("Timing", [
    "Delay", "RetriggerableDelay", "SetTimerByFunctionName",
    "ClearTimerByFunctionName", "TimerByFunction", "ResetDoOnce",
])
_assign("Actor", [
    "GetActorLocation", "SetActorLocation", "GetActorRotation", "SetActorRotation",
    "GetActorForwardVector", "GetForwardVector", "AddActorLocalRotation",
    "AddActorLocalOffset", "GetDistanceTo", "GetDistanceToActor",
    "SetActorHiddenInGame", "TeleportTo", "DestroyActor",
    "IsValid", "ActorHasTag", "GetActorHasTag", "GetActorTags",
    "SetVisibility", "ToggleVisibility", "RotateActorOnAxis",
    "GetWorldLocation", "GetWorldRotation",
])
_assign("Gameplay", [
    "GetPlayerPawn", "GetPlayerCharacter", "GetWorldDeltaSeconds",
    "PlaySoundAtLocation", "SpawnActorFromClass",
    "GetGameTimeInSeconds", "GetGameTimeSeconds", "GetActorArray",
])
_assign("Physics", [
    "SetSimulatePhysics", "AddImpulse", "AddForce",
    "AddForceAtLocation", "AddImpulseAtLocation", "AddDownwardForce",
])
_assign("Math — Float", [
    "AddFloat", "SubtractFloat", "MultiplyFloat", "DivideFloat",
    "ClampFloat", "RandomFloat", "RandomFloatInRange", "SelectFloat",
    "Max", "MaxFloat", "Min", "Lerp",
    "AddToHealth", "AddToArmor", "AddToPlayerScore",
    "AddToPlayerHealth", "AddToPlayerArmor",
])
_assign("Math — Int", [
    "AddInt", "SubtractInt", "RandomInteger", "Modulo",
    "IncInteger", "GetRandomInt",
])
_assign("Math — Comparison", [
    "LessThan", "GreaterThan", "LessEqual", "LessEqualFloat",
    "EqualEqual", "GreaterEqualFloat", "GreaterEqualInt",
    "GreaterThanFloat", "LessThanFloat", "GreaterEqual",
    "NotEqual", "NotEqualEqual",
])
_assign("Math — Boolean", [
    "Not", "NotBool", "NOT", "And", "BooleanAND", "Or", "BooleanOR",
])
_assign("Math — Trig", [
    "Sin",
])
_assign("Vector", [
    "MakeVector", "Vector", "BreakVector", "VectorLerp", "Vector_Lerp",
    "VectorDistance", "Vector_Distance", "VSize", "VectorLength",
    "SubtractVector", "VectorMultiply", "AddVector", "AddVectors",
])
_assign("Rotator", [
    "MakeRotator",
])
_assign("String", [
    "Concatenate", "AppendText", "GetDisplayName", "GetDisplayText",
    "GetLength", "IntToString", "ToString", "ConvertToText",
])
_assign("UI / Widget", [
    "CreateWidget", "AddToViewport", "AddToPlayerScreen",
    "RemoveFromParent", "SetText",
])
_assign("Array", [
    "ArrayLength", "GetArrayLength", "GetArraySize",
    "Contains", "ArrayContains",
    "ClearArray", "ArrayClear",
    "Get", "GetArrayItemAtIndex", "ArrayGet", "GetArrayElement", "GetElementAtIndex",
    "RemoveAt", "ArrayRemoveIndex", "ArrayRemove",
    "AddUnique", "ArrayAdd", "AddActor",
])
_assign("Movement", [
    "AddMovementInput", "GetInputAxisValue", "MoveTo",
])
_assign("Trace", [
    "LineTraceSingle", "BreakHitResult", "GetHitNormal",
])
_assign("Misc", [
    "GetWorld", "OpenGate", "CloseGate", "EnterGate",
])

# ── Descriptions ──────────────────────────────────────────────────

_DESC = {
    # Events
    "Event_BeginPlay": "Fires once when the actor is spawned or the game starts",
    "Event_Tick": "Fires every frame. Use DeltaSeconds for frame-independent logic",
    "Event_EndPlay": "Fires when the actor is destroyed or the game ends",
    "Event_ActorBeginOverlap": "Fires when another actor starts overlapping this actor",
    "Event_ActorEndOverlap": "Fires when another actor stops overlapping this actor",
    "Event_AnyDamage": "Fires when this actor receives damage from ApplyDamage",
    "Event_Hit": "Fires when this actor collides with a physics object",
    "Event_InputAction": "Fires when a bound input action key is pressed or released",
    "Event_CustomEvent": "A named event that can be called by SetTimerByFunctionName or CallFunction",
    "Event_Custom": "A named event that can be called by SetTimerByFunctionName or CallFunction",

    # Flow Control
    "Branch": "If/else: routes execution based on a boolean condition",
    "Sequence": "Executes multiple output chains in order (A, B, C...)",
    "FlipFlop": "Alternates between A and B outputs on each execution",
    "DoOnce": "Executes the output only the first time; Reset pin re-enables it",
    "Gate": "Controllable pass-through: Enter fires Exit only when gate is open",
    "MultiGate": "Routes execution to one of several outputs, cycling through them",

    # Loops
    "ForLoop": "Loop from FirstIndex to LastIndex. LoopBody fires each iteration",
    "ForEachLoop": "Iterates over each element in an array",
    "WhileLoop": "Repeats LoopBody while Condition is true",

    # Casting
    "CastToCharacter": "Attempts to cast an object to Character class",
    "CastToPawn": "Attempts to cast an object to Pawn class",
    "CastToPlayerController": "Attempts to cast an object to PlayerController class",

    # Variables
    "VariableGet": "Read the value of a Blueprint variable",
    "GetVar": "Read the value of a Blueprint variable",
    "VariableSet": "Write a new value to a Blueprint variable",
    "SetVar": "Write a new value to a Blueprint variable",
    "GetVariable": "Read the value of a Blueprint variable",
    "SetVariable": "Write a new value to a Blueprint variable",

    # Switch
    "SwitchOnInt": "Routes execution to a numbered case based on an integer value",
    "SwitchOnString": "Routes execution to a named case based on a string value",

    # Debug
    "PrintString": "Print a string to the screen and output log (debug only)",
    "Print": "Print a string to the screen and output log (debug only)",

    # Timing
    "Delay": "Pauses execution for a specified duration, then continues",
    "RetriggerableDelay": "Like Delay, but restarting resets the timer instead of queuing",
    "SetTimerByFunctionName": "Starts a timer that calls a custom event by name",
    "ClearTimerByFunctionName": "Stops a running timer by its function name",

    # Actor
    "GetActorLocation": "Returns the actor's current world position as a Vector",
    "SetActorLocation": "Teleports the actor to a new world position",
    "GetActorRotation": "Returns the actor's current world rotation",
    "SetActorRotation": "Sets the actor's world rotation",
    "GetActorForwardVector": "Returns a unit vector pointing in the actor's forward direction",
    "AddActorLocalRotation": "Adds a relative rotation to the actor",
    "AddActorLocalOffset": "Moves the actor by a relative offset",
    "GetDistanceTo": "Returns the distance in units between this actor and another",
    "SetActorHiddenInGame": "Shows or hides the actor at runtime",
    "TeleportTo": "Teleports the actor to a location (handles collision checks)",
    "DestroyActor": "Removes this actor from the world immediately",
    "IsValid": "Checks if an object reference is valid (not null or pending kill)",
    "ActorHasTag": "Returns true if the actor has a specific tag",
    "SetVisibility": "Shows or hides a scene component",
    "ToggleVisibility": "Flips a component's visibility state",

    # Gameplay
    "GetPlayerPawn": "Returns a reference to the player's pawn (player index 0)",
    "GetPlayerCharacter": "Returns a reference to the player's character",
    "GetWorldDeltaSeconds": "Returns the time elapsed since the last frame in seconds",
    "PlaySoundAtLocation": "Plays a sound effect at a world position",
    "SpawnActorFromClass": "Creates a new actor of the specified class at a transform",
    "GetGameTimeInSeconds": "Returns total elapsed game time in seconds",
    "GetActorArray": "Returns an array of all actors of the specified class",

    # Physics
    "SetSimulatePhysics": "Enables or disables physics simulation on a component",
    "AddImpulse": "Applies an instant force to a physics-enabled component",
    "AddForce": "Applies a continuous force to a physics-enabled component",
    "AddForceAtLocation": "Applies a continuous force at a specific world position",
    "AddImpulseAtLocation": "Applies an instant force at a specific world position",

    # Math — Float
    "AddFloat": "Add two float values (A + B)",
    "SubtractFloat": "Subtract two float values (A - B)",
    "MultiplyFloat": "Multiply two float values (A * B)",
    "DivideFloat": "Divide two float values (A / B)",
    "ClampFloat": "Clamps a value between Min and Max",
    "RandomFloat": "Returns a random float between 0 and 1",
    "RandomFloatInRange": "Returns a random float between Min and Max",
    "SelectFloat": "Returns A or B depending on the Select boolean",
    "Max": "Returns the larger of two float values",
    "Min": "Returns the smaller of two float values",
    "Lerp": "Linear interpolation between A and B by Alpha (0-1)",

    # Math — Int
    "AddInt": "Add two integer values (A + B)",
    "SubtractInt": "Subtract two integer values (A - B)",
    "RandomInteger": "Returns a random integer from 0 to Max-1",
    "Modulo": "Integer remainder of A divided by B",

    # Math — Comparison
    "LessThan": "Returns true if A < B",
    "GreaterThan": "Returns true if A > B",
    "LessEqual": "Returns true if A <= B",
    "GreaterEqual": "Returns true if A >= B",
    "EqualEqual": "Returns true if A == B",
    "NotEqual": "Returns true if A != B",

    # Math — Boolean
    "Not": "Inverts a boolean value (true→false, false→true)",
    "And": "Returns true only if both A and B are true",
    "Or": "Returns true if either A or B is true",

    # Math — Trig
    "Sin": "Returns the sine of an angle in radians",

    # Vector
    "MakeVector": "Constructs a Vector from X, Y, Z components",
    "BreakVector": "Splits a Vector into its X, Y, Z components",
    "VectorLerp": "Linear interpolation between two vectors",
    "VectorDistance": "Returns the distance between two points",
    "VSize": "Returns the length (magnitude) of a vector",
    "SubtractVector": "Subtract two vectors (A - B)",
    "VectorMultiply": "Scale a vector by a float (A * B)",
    "AddVector": "Add two vectors (A + B)",

    # Rotator
    "MakeRotator": "Constructs a Rotator from Roll, Pitch, Yaw in degrees",

    # String
    "Concatenate": "Joins two strings together (A + B)",
    "GetDisplayName": "Returns the human-readable display name of an object",
    "GetLength": "Returns the number of characters in a string",
    "IntToString": "Converts an integer to its string representation",
    "ToString": "Converts a float to its string representation",

    # UI / Widget
    "CreateWidget": "Creates a new UMG widget instance from a widget class",
    "AddToViewport": "Adds a widget to the player's screen",
    "RemoveFromParent": "Removes a widget from the screen",
    "SetText": "Sets the text content of a TextBlock widget",

    # Array
    "ArrayLength": "Returns the number of elements in an array",
    "Contains": "Returns true if the array contains the specified item",
    "ClearArray": "Removes all elements from an array",
    "Get": "Returns the element at the specified index",
    "RemoveAt": "Removes the element at the specified index",
    "AddUnique": "Adds an item to the array only if it's not already present",
    "ArrayAdd": "Adds an item to the end of the array",

    # Movement
    "AddMovementInput": "Adds movement input along a direction with a scale value",
    "GetInputAxisValue": "Returns the current value of a named input axis",
    "MoveTo": "Moves an AI-controlled pawn to a location (SimpleMoveToLocation)",

    # Trace
    "LineTraceSingle": "Casts a ray from Start to End, returns true if it hits something",
    "BreakHitResult": "Extracts Location, Normal, and other data from a hit result",

    # Misc
    "GetWorld": "Returns a reference to the current world object",
    "OpenGate": "Opens a Gate node, allowing execution to pass through",
    "CloseGate": "Closes a Gate node, blocking execution",
}

# ── Pin descriptions (important nodes only) ──────────────────────

_PIN_DESC = {
    ("SetTimerByFunctionName", "FunctionName"): "Name of the custom event to call",
    ("SetTimerByFunctionName", "Time"): "Interval in seconds",
    ("SetTimerByFunctionName", "Looping"): "Whether to repeat the timer",
    ("Delay", "Duration"): "Time to wait in seconds",
    ("Branch", "Condition"): "Boolean value that determines which path to take",
    ("PrintString", "InString"): "The text to display on screen",
    ("ForLoop", "FirstIndex"): "Starting loop index (inclusive)",
    ("ForLoop", "LastIndex"): "Ending loop index (inclusive)",
    ("ForLoop", "Index"): "Current iteration index",
    ("ForEachLoop", "Array"): "The array to iterate over",
    ("ForEachLoop", "Element"): "Current element value",
    ("ForEachLoop", "Index"): "Current element index",
    ("WhileLoop", "Condition"): "Loop continues while this is true",
    ("SpawnActorFromClass", "ActorClass"): "The Blueprint class to spawn",
    ("SpawnActorFromClass", "SpawnTransform"): "Where to spawn (location/rotation/scale)",
    ("ClampFloat", "Value"): "The value to clamp",
    ("ClampFloat", "Min"): "Minimum allowed value",
    ("ClampFloat", "Max"): "Maximum allowed value",
    ("Event_Tick", "DeltaSeconds"): "Time elapsed since the last frame",
    ("Event_ActorBeginOverlap", "OtherActor"): "The actor that started overlapping",
    ("Event_AnyDamage", "Damage"): "Amount of damage received",
    ("PlaySoundAtLocation", "Sound"): "Sound asset to play",
    ("PlaySoundAtLocation", "Location"): "World position to play the sound at",
    ("AddMovementInput", "WorldDirection"): "Direction to move in (world space)",
    ("AddMovementInput", "ScaleValue"): "Movement speed multiplier (0-1)",
    ("LineTraceSingle", "Start"): "Ray start position (world space)",
    ("LineTraceSingle", "End"): "Ray end position (world space)",
    ("SwitchOnInt", "Selection"): "Integer value to match against cases",
    ("SwitchOnString", "Selection"): "String value to match against cases",
    ("GetDistanceTo", "OtherActor"): "The actor to measure distance to",
    ("Lerp", "Alpha"): "Interpolation factor (0 = A, 1 = B)",
    ("SelectFloat", "Select"): "If true returns A, if false returns B",
    ("ClearTimerByFunctionName", "FunctionName"): "Name of the timer to stop",
    ("RetriggerableDelay", "Duration"): "Time to wait in seconds (resets if retriggered)",
    ("CreateWidget", "WidgetClass"): "The Widget Blueprint class to create",
    ("AddToViewport", "Target"): "The widget instance to add to screen",
    ("SetText", "InText"): "The new text content",
    ("Event_InputAction", "ActionName"): "The input action name to listen for",
    ("GetInputAxisValue", "AxisName"): "The input axis name to read",
    ("MoveTo", "Goal"): "Target world location for the AI to move to",
    ("SetActorLocation", "NewLocation"): "The new world position",
    ("TeleportTo", "DestLocation"): "Destination position in world space",
    ("SetActorHiddenInGame", "bNewHidden"): "True to hide, false to show",
    ("SetSimulatePhysics", "bSimulate"): "True to enable physics, false to disable",
    ("AddImpulse", "Impulse"): "Force vector to apply instantly",
    ("SetActorRotation", "NewRotation"): "The new world rotation",
    ("AddActorLocalRotation", "DeltaRotation"): "Rotation to add (relative to actor)",
    ("AddActorLocalOffset", "DeltaLocation"): "Offset to move by (relative to actor)",
    ("SetVisibility", "bNewVisibility"): "True to show, false to hide",
    ("ActorHasTag", "Tag"): "The tag name to check for",
    ("RandomFloatInRange", "Min"): "Minimum value (inclusive)",
    ("RandomFloatInRange", "Max"): "Maximum value (inclusive)",
    ("RandomInteger", "Max"): "Upper bound (exclusive)",
    ("MakeVector", "X"): "X component",
    ("MakeVector", "Y"): "Y component",
    ("MakeVector", "Z"): "Z component",
    ("MakeRotator", "Roll"): "Roll angle in degrees",
    ("MakeRotator", "Pitch"): "Pitch angle in degrees",
    ("MakeRotator", "Yaw"): "Yaw angle in degrees",
}


def _get_category(node_type):
    """Get category for a node type."""
    if node_type in _CAT:
        return _CAT[node_type]
    # Dynamic CastTo<X>
    if node_type.startswith("CastTo"):
        return "Casting"
    # VariableGet_X / VariableSet_X
    if node_type.startswith("VariableGet_") or node_type.startswith("VariableSet_"):
        return "Variables"
    return "Misc"


def _get_description(node_type):
    """Get description for a node type."""
    if node_type in _DESC:
        return _DESC[node_type]
    # Check canonical via aliases
    canonical, _ = resolve(node_type)
    if canonical in _DESC:
        return _DESC[canonical]
    # Generate dynamic descriptions
    if node_type.startswith("CastTo"):
        cls = node_type[6:]
        return f"Attempts to cast an object to {cls} class"
    if node_type.startswith("VariableGet_"):
        return f"Read the value of variable '{node_type[12:]}'"
    if node_type.startswith("VariableSet_"):
        return f"Write a value to variable '{node_type[12:]}'"
    return "Blueprint node"


def _build_pins(node_type, mapping):
    """Build input_pins and output_pins arrays from node_map data."""
    input_pins = []
    output_pins = []

    # Exec inputs
    for pin in mapping.get("exec_in", []):
        input_pins.append({
            "name": pin,
            "type": "Exec",
            "description": _PIN_DESC.get((node_type, pin), ""),
        })

    # Data inputs
    for name, ptype in mapping.get("data_in", {}).items():
        input_pins.append({
            "name": name,
            "type": ptype.capitalize(),
            "description": _PIN_DESC.get((node_type, name), ""),
        })

    # Exec outputs
    for pin in mapping.get("exec_out", []):
        output_pins.append({
            "name": pin,
            "type": "Exec",
            "description": _PIN_DESC.get((node_type, pin), ""),
        })

    # Data outputs
    for name, ptype in mapping.get("data_out", {}).items():
        output_pins.append({
            "name": name,
            "type": ptype.capitalize(),
            "description": _PIN_DESC.get((node_type, name), ""),
        })

    return input_pins, output_pins


def get_reference(node_type):
    """Get complete reference for a node type.

    Returns dict with: node_type, category, description, input_pins, output_pins, aliases.
    Returns None if node type is unknown.
    """
    canonical, mapping = resolve(node_type)
    if mapping is None:
        return None

    input_pins, output_pins = _build_pins(canonical, mapping)

    # Find aliases that point to this canonical name
    aliases = [alias for alias, target in ALIASES.items() if target == canonical]

    result = {
        "node_type": canonical,
        "category": _get_category(canonical),
        "description": _get_description(canonical),
        "input_pins": input_pins,
        "output_pins": output_pins,
    }
    if aliases:
        result["aliases"] = aliases
    if node_type != canonical:
        result["resolved_from"] = node_type

    return result


def list_types():
    """Return all node types organized by category.

    Returns dict: {category: [{node_type, description}, ...], ...}
    Excludes obvious duplicates/aliases to keep the catalog clean.
    """
    # Deduplicate: skip entries whose mapping is identical to another entry
    seen_funcs = {}
    canonical_types = []

    for name, mapping in NODE_MAP.items():
        # Create a signature for dedup
        sig = (
            mapping.get("ue_class", ""),
            mapping.get("ue_function", ""),
            mapping.get("ue_event", ""),
        )
        if sig in seen_funcs:
            continue
        seen_funcs[sig] = name
        canonical_types.append(name)

    # Also include the ALIASES targets that might not be in canonical_types
    # (they already are since they're in NODE_MAP)

    # Build category → nodes mapping
    categories = {}
    for name in canonical_types:
        cat = _get_category(name)
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "node_type": name,
            "description": _get_description(name),
        })

    return {
        "total_types": len(canonical_types),
        "categories": categories,
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1:
        ref = get_reference(sys.argv[1])
        if ref:
            print(json.dumps(ref, indent=2))
        else:
            print(f"Unknown node type: {sys.argv[1]}")
    else:
        result = list_types()
        print(f"Total canonical types: {result['total_types']}")
        for cat, nodes in result["categories"].items():
            print(f"\n{cat} ({len(nodes)}):")
            for n in nodes:
                print(f"  {n['node_type']}: {n['description']}")
