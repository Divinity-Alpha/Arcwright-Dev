"""
BlueprintLLM — Behavior Tree Node Map
Maps DSL node names to UE5 Behavior Tree classes.
"""

# ─── Composite Nodes ─────────────────────────────────────────────────────────

COMPOSITES = {
    "Selector": {
        "ue_class": "UBTComposite_Selector",
        "description": "Tries children left to right, succeeds on first success (OR)",
    },
    "Sequence": {
        "ue_class": "UBTComposite_Sequence",
        "description": "Tries children left to right, fails on first failure (AND)",
    },
    "SimpleParallel": {
        "ue_class": "UBTComposite_SimpleParallel",
        "description": "Runs main task and background subtree simultaneously",
        "params": ["FinishMode"],  # Immediate, Delayed
    },
}

# ─── Task Nodes (Leaf) ───────────────────────────────────────────────────────

TASKS = {
    # Built-in UE tasks
    "MoveTo": {
        "ue_class": "UBTTask_MoveTo",
        "params": ["Key", "AcceptableRadius", "FilterClass", "AllowStrafe",
                   "AllowPartialPath", "TrackMovingGoal", "ProjectGoalLocation"],
        "required_params": ["Key"],
        "description": "Navigate AI to blackboard location or actor",
    },
    "Wait": {
        "ue_class": "UBTTask_Wait",
        "params": ["Duration", "RandomDeviation"],
        "required_params": ["Duration"],
        "description": "Wait for a specified duration",
    },
    "WaitBlackboardTime": {
        "ue_class": "UBTTask_WaitBlackboardTime",
        "params": ["Key"],
        "required_params": ["Key"],
        "description": "Wait for duration stored in blackboard key",
    },
    "RotateToFaceBBEntry": {
        "ue_class": "UBTTask_RotateToFaceBBEntry",
        "params": ["Key", "Precision"],
        "required_params": ["Key"],
        "description": "Rotate AI to face blackboard actor/location",
    },
    "PlaySound": {
        "ue_class": "UBTTask_PlaySound",
        "params": ["Sound"],
        "required_params": ["Sound"],
        "description": "Play a sound asset",
    },
    "PlayAnimation": {
        "ue_class": "UBTTask_PlayAnimation",
        "params": ["Animation", "bLooping", "bNonBlocking"],
        "description": "Play an animation montage",
    },
    "RunBehavior": {
        "ue_class": "UBTTask_RunBehavior",
        "params": ["BehaviorTree"],
        "required_params": ["BehaviorTree"],
        "description": "Run a sub-behavior tree",
    },
    "SetTagCooldown": {
        "ue_class": "UBTTask_SetTagCooldown",
        "params": ["Tag", "Duration", "bAddToExistingDuration"],
        "required_params": ["Tag", "Duration"],
        "description": "Set a gameplay tag cooldown",
    },
    "FinishWithResult": {
        "ue_class": "UBTTask_FinishWithResult",
        "params": ["Result"],  # Succeeded, Failed
        "required_params": ["Result"],
        "description": "Force a specific result",
    },

    # Custom BlueprintLLM extension tasks
    "SetBlackboardValue": {
        "ue_class": "UBTTask_BlueprintBase",
        "custom": True,
        "params": ["Key", "Value"],
        "required_params": ["Key", "Value"],
        "description": "Write a value to a blackboard key",
    },
    "ClearBlackboardValue": {
        "ue_class": "UBTTask_BlueprintBase",
        "custom": True,
        "params": ["Key"],
        "required_params": ["Key"],
        "description": "Clear/reset a blackboard key",
    },
    "PrintString": {
        "ue_class": "UBTTask_BlueprintBase",
        "custom": True,
        "params": ["Message"],
        "required_params": ["Message"],
        "description": "Debug print (development only)",
    },
    "ApplyDamage": {
        "ue_class": "UBTTask_BlueprintBase",
        "custom": True,
        "params": ["Key", "Damage"],
        "required_params": ["Key", "Damage"],
        "description": "Apply damage to target actor from blackboard",
    },
    "SpawnActor": {
        "ue_class": "UBTTask_BlueprintBase",
        "custom": True,
        "params": ["Class", "Key"],
        "required_params": ["Class"],
        "description": "Spawn actor at blackboard location",
    },
    "DestroyActor": {
        "ue_class": "UBTTask_BlueprintBase",
        "custom": True,
        "params": ["Key"],
        "required_params": ["Key"],
        "description": "Destroy blackboard actor",
    },
    "FireEvent": {
        "ue_class": "UBTTask_BlueprintBase",
        "custom": True,
        "params": ["EventName"],
        "required_params": ["EventName"],
        "description": "Trigger a custom event on the AI's pawn",
    },
}

# ─── Decorator Nodes (Conditions) ────────────────────────────────────────────

DECORATORS = {
    "BlackboardBased": {
        "ue_class": "UBTDecorator_BlackboardBased",
        "params": ["Key", "Condition", "Value", "AbortMode"],
        "required_params": ["Key", "Condition"],
        "conditions": ["IsSet", "IsNotSet", "Equals", "NotEquals",
                       "LessThan", "GreaterThan", "LessEqual", "GreaterEqual"],
        "description": "Check a blackboard key value",
    },
    "CompareBBEntries": {
        "ue_class": "UBTDecorator_CompareBBEntries",
        "params": ["KeyA", "KeyB", "Operator"],
        "required_params": ["KeyA", "KeyB", "Operator"],
        "description": "Compare two blackboard values",
    },
    "ConeCheck": {
        "ue_class": "UBTDecorator_ConeCheck",
        "params": ["ConeOrigin", "ObservedKey", "ConeHalfAngle"],
        "required_params": ["ConeOrigin", "ObservedKey", "ConeHalfAngle"],
        "description": "Check if target is within a cone",
    },
    "Cooldown": {
        "ue_class": "UBTDecorator_Cooldown",
        "params": ["Duration"],
        "required_params": ["Duration"],
        "description": "Prevent re-execution for N seconds",
    },
    "DoesPathExist": {
        "ue_class": "UBTDecorator_DoesPathExist",
        "params": ["StartKey", "EndKey", "PathQueryType"],
        "required_params": ["StartKey", "EndKey"],
        "description": "Check navmesh reachability",
    },
    "ForceSuccess": {
        "ue_class": "UBTDecorator_ForceSuccess",
        "params": [],
        "description": "Always return success regardless of child result",
    },
    "IsAtLocation": {
        "ue_class": "UBTDecorator_IsAtLocation",
        "params": ["Key", "AcceptableRadius"],
        "required_params": ["Key"],
        "description": "Check if AI is near blackboard location",
    },
    "IsBBEntryOfClass": {
        "ue_class": "UBTDecorator_IsBBEntryOfClass",
        "params": ["Key", "TestClass"],
        "required_params": ["Key", "TestClass"],
        "description": "Type check on blackboard object",
    },
    "KeepInCone": {
        "ue_class": "UBTDecorator_KeepInCone",
        "params": ["ConeOrigin", "ObservedKey", "ConeHalfAngle"],
        "required_params": ["ConeOrigin", "ObservedKey"],
        "description": "Abort if target leaves vision cone",
    },
    "Loop": {
        "ue_class": "UBTDecorator_Loop",
        "params": ["NumLoops", "InfiniteLoop"],
        "description": "Repeat child N times or infinitely",
    },
    "TagCooldown": {
        "ue_class": "UBTDecorator_TagCooldown",
        "params": ["Tag", "Duration", "bAddToExistingDuration"],
        "required_params": ["Tag", "Duration"],
        "description": "Cooldown by gameplay tag",
    },
    "TimeLimit": {
        "ue_class": "UBTDecorator_TimeLimit",
        "params": ["Duration"],
        "required_params": ["Duration"],
        "description": "Abort if branch takes too long",
    },
}

# ─── Service Nodes (Background Tick) ─────────────────────────────────────────

SERVICES = {
    "DefaultFocus": {
        "ue_class": "UBTService_DefaultFocus",
        "params": ["Key"],
        "required_params": ["Key"],
        "description": "Set AI focus to blackboard actor",
    },
    "RunEQS": {
        "ue_class": "UBTService_RunEQS",
        "params": ["QueryTemplate"],
        "required_params": ["QueryTemplate"],
        "description": "Run an Environment Query periodically",
    },

    # Custom BlueprintLLM extension services
    "UpdateDistance": {
        "ue_class": "UBTService_BlueprintBase",
        "custom": True,
        "params": ["TargetKey", "ResultKey", "Interval"],
        "required_params": ["TargetKey", "ResultKey"],
        "description": "Calculate distance to target, store in blackboard",
    },
    "FindNearestActor": {
        "ue_class": "UBTService_BlueprintBase",
        "custom": True,
        "params": ["Class", "ResultKey", "SearchRadius", "Interval"],
        "required_params": ["ResultKey"],
        "description": "Find closest actor of class, store in blackboard",
    },
    "CheckLineOfSight": {
        "ue_class": "UBTService_BlueprintBase",
        "custom": True,
        "params": ["TargetKey", "ResultKey", "Interval"],
        "required_params": ["TargetKey", "ResultKey"],
        "description": "Line trace to target, store bool in blackboard",
    },
    "UpdateBlackboard": {
        "ue_class": "UBTService_BlueprintBase",
        "custom": True,
        "params": ["Key", "Value", "Interval"],
        "required_params": ["Key", "Value"],
        "description": "Set a blackboard key to a value periodically",
    },
}

# ─── Abort Modes ─────────────────────────────────────────────────────────────

ABORT_MODES = {
    "None": "EBTFlowAbortMode::None",
    "Self": "EBTFlowAbortMode::Self",
    "LowerPriority": "EBTFlowAbortMode::LowerPriority",
    "Both": "EBTFlowAbortMode::Both",
}

# ─── Blackboard Key Types ────────────────────────────────────────────────────

KEY_TYPES = {
    "Object": "UBlackboardKeyType_Object",
    "Vector": "UBlackboardKeyType_Vector",
    "Float": "UBlackboardKeyType_Float",
    "Int": "UBlackboardKeyType_Int",
    "Bool": "UBlackboardKeyType_Bool",
    "String": "UBlackboardKeyType_String",
    "Class": "UBlackboardKeyType_Class",
    "Enum": "UBlackboardKeyType_Enum",
    "Rotator": "UBlackboardKeyType_Rotator",
    "Name": "UBlackboardKeyType_Name",
}

# ─── Aliases ─────────────────────────────────────────────────────────────────

ALIASES = {
    # Composite aliases
    "Select": "Selector",
    "Sel": "Selector",
    "Seq": "Sequence",
    "Parallel": "SimpleParallel",

    # Task aliases
    "Move": "MoveTo",
    "MoveToTarget": "MoveTo",
    "MoveToLocation": "MoveTo",
    "Delay": "Wait",
    "WaitTime": "Wait",
    "FaceTarget": "RotateToFaceBBEntry",
    "LookAt": "RotateToFaceBBEntry",
    "Attack": "ApplyDamage",
    "Damage": "ApplyDamage",
    "Print": "PrintString",
    "Debug": "PrintString",
    "Spawn": "SpawnActor",
    "Destroy": "DestroyActor",
    "SetBB": "SetBlackboardValue",
    "ClearBB": "ClearBlackboardValue",
    "RunSubTree": "RunBehavior",
    "SubTree": "RunBehavior",

    # Decorator aliases
    "BB": "BlackboardBased",
    "BBCheck": "BlackboardBased",
    "CheckBlackboard": "BlackboardBased",
    "CompareBB": "CompareBBEntries",
    "InCone": "ConeCheck",
    "AtLocation": "IsAtLocation",
    "NearLocation": "IsAtLocation",
    "ClassCheck": "IsBBEntryOfClass",
    "Repeat": "Loop",
    "Timeout": "TimeLimit",

    # Service aliases
    "Focus": "DefaultFocus",
    "TrackDistance": "UpdateDistance",
    "FindNearest": "FindNearestActor",
    "LOSCheck": "CheckLineOfSight",
    "SightCheck": "CheckLineOfSight",
    "SetBBPeriodic": "UpdateBlackboard",
}


def resolve_node(name: str, category: str = None):
    """
    Resolve a DSL node name to its canonical name and mapping.
    
    Args:
        name: DSL node name (may be an alias)
        category: Optional hint — "composite", "task", "decorator", "service"
    
    Returns:
        (canonical_name, mapping_dict, node_category) or (name, None, None) if not found
    """
    # Check aliases first
    canonical = ALIASES.get(name, name)
    
    # Search in category order (or specific category if hinted)
    search_order = []
    if category:
        cat_map = {
            "composite": [(COMPOSITES, "composite")],
            "task": [(TASKS, "task")],
            "decorator": [(DECORATORS, "decorator")],
            "service": [(SERVICES, "service")],
        }
        search_order = cat_map.get(category, [])
    
    if not search_order:
        search_order = [
            (COMPOSITES, "composite"),
            (TASKS, "task"),
            (DECORATORS, "decorator"),
            (SERVICES, "service"),
        ]
    
    for node_map, cat in search_order:
        if canonical in node_map:
            return canonical, node_map[canonical], cat
    
    return name, None, None


def get_all_node_names():
    """Return all known node names including aliases."""
    names = set()
    names.update(COMPOSITES.keys())
    names.update(TASKS.keys())
    names.update(DECORATORS.keys())
    names.update(SERVICES.keys())
    names.update(ALIASES.keys())
    return sorted(names)


def get_stats():
    """Return node map statistics."""
    return {
        "composites": len(COMPOSITES),
        "tasks": len(TASKS),
        "decorators": len(DECORATORS),
        "services": len(SERVICES),
        "aliases": len(ALIASES),
        "total": len(COMPOSITES) + len(TASKS) + len(DECORATORS) + len(SERVICES),
    }
