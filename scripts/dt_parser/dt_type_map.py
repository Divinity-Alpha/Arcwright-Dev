"""
BlueprintLLM — Data Table Type Map
Maps DSL column types to UE5 property types.
"""

# ─── Column Types ────────────────────────────────────────────────────────────

COLUMN_TYPES = {
    # Primitive types
    "String": {
        "ue_type": "FString",
        "cpp_type": "FString",
        "category": "primitive",
        "default": "",
        "parse": lambda v: str(v).strip('"'),
    },
    "Name": {
        "ue_type": "FName",
        "cpp_type": "FName",
        "category": "primitive",
        "default": "",
        "parse": lambda v: str(v).strip('"'),
    },
    "Text": {
        "ue_type": "FText",
        "cpp_type": "FText",
        "category": "primitive",
        "default": "",
        "parse": lambda v: str(v).strip('"'),
    },
    "Int": {
        "ue_type": "int32",
        "cpp_type": "int32",
        "category": "numeric",
        "default": 0,
        "parse": lambda v: int(v),
    },
    "Float": {
        "ue_type": "float",
        "cpp_type": "float",
        "category": "numeric",
        "default": 0.0,
        "parse": lambda v: float(v),
    },
    "Bool": {
        "ue_type": "bool",
        "cpp_type": "bool",
        "category": "primitive",
        "default": False,
        "parse": lambda v: v.lower() in ("true", "1", "yes"),
    },
    "Vector": {
        "ue_type": "FVector",
        "cpp_type": "FVector",
        "category": "struct",
        "default": {"x": 0, "y": 0, "z": 0},
        "parse": "vector",
    },
    "Rotator": {
        "ue_type": "FRotator",
        "cpp_type": "FRotator",
        "category": "struct",
        "default": {"pitch": 0, "yaw": 0, "roll": 0},
        "parse": "rotator",
    },
    "Color": {
        "ue_type": "FLinearColor",
        "cpp_type": "FLinearColor",
        "category": "struct",
        "default": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
        "parse": "color",
    },
}

# Asset reference types — resolved dynamically via "Asset:<subtype>"
ASSET_SUBTYPES = {
    "StaticMesh": "TSoftObjectPtr<UStaticMesh>",
    "Texture": "TSoftObjectPtr<UTexture2D>",
    "Sound": "TSoftObjectPtr<USoundBase>",
    "Blueprint": "TSoftClassPtr<AActor>",
    "Material": "TSoftObjectPtr<UMaterialInterface>",
    "AnimMontage": "TSoftObjectPtr<UAnimMontage>",
    "BehaviorTree": "TSoftObjectPtr<UBehaviorTree>",
    "NiagaraSystem": "TSoftObjectPtr<UNiagaraSystem>",
    "DataTable": "TSoftObjectPtr<UDataTable>",
    "WidgetBlueprint": "TSoftClassPtr<UUserWidget>",
}

# Type aliases for convenience
ALIASES = {
    "Str": "String",
    "Txt": "Text",
    "Integer": "Int",
    "Double": "Float",
    "Boolean": "Bool",
    "Vec": "Vector",
    "Rot": "Rotator",
    "Vec3": "Vector",
    "FVector": "Vector",
    "FRotator": "Rotator",
    "FColor": "Color",
    "FLinearColor": "Color",
    "FString": "String",
    "FName": "Name",
    "FText": "Text",
}


def resolve_type(type_str: str) -> dict:
    """
    Resolve a DSL type string to type info.
    
    Handles:
        "String"          → basic type
        "Asset:StaticMesh"→ asset reference
        "Enum:ERarity"    → enum type
        "Array:Int"       → array of type
        "Struct:FMyStruct" → nested struct
    
    Returns: {"name": ..., "ue_type": ..., "category": ..., "subtype": ...}
    """
    # Check aliases
    canonical = ALIASES.get(type_str, type_str)
    
    # Basic types
    if canonical in COLUMN_TYPES:
        info = COLUMN_TYPES[canonical]
        return {
            "name": canonical,
            "ue_type": info["ue_type"],
            "cpp_type": info["cpp_type"],
            "category": info["category"],
            "default": info["default"],
        }
    
    # Asset references: Asset:StaticMesh
    if canonical.startswith("Asset:"):
        subtype = canonical.split(":", 1)[1]
        ue_type = ASSET_SUBTYPES.get(subtype, f"TSoftObjectPtr<U{subtype}>")
        return {
            "name": canonical,
            "ue_type": ue_type,
            "cpp_type": ue_type,
            "category": "asset",
            "subtype": subtype,
            "default": "",
        }
    
    # Enum: Enum:ERarity
    if canonical.startswith("Enum:"):
        enum_name = canonical.split(":", 1)[1]
        return {
            "name": canonical,
            "ue_type": enum_name,
            "cpp_type": f"E{enum_name}" if not enum_name.startswith("E") else enum_name,
            "category": "enum",
            "subtype": enum_name,
            "default": "",
        }
    
    # Array: Array:Int, Array:String
    if canonical.startswith("Array:"):
        element_type_str = canonical.split(":", 1)[1]
        element = resolve_type(element_type_str)
        return {
            "name": canonical,
            "ue_type": f"TArray<{element['ue_type']}>",
            "cpp_type": f"TArray<{element['cpp_type']}>",
            "category": "array",
            "element_type": element,
            "default": [],
        }
    
    # Struct: Struct:FMyStruct
    if canonical.startswith("Struct:"):
        struct_name = canonical.split(":", 1)[1]
        return {
            "name": canonical,
            "ue_type": struct_name,
            "cpp_type": struct_name,
            "category": "struct",
            "subtype": struct_name,
            "default": {},
        }
    
    # Unknown type
    return {
        "name": type_str,
        "ue_type": "UNKNOWN",
        "cpp_type": "UNKNOWN",
        "category": "unknown",
        "default": None,
    }


def parse_value(value_str: str, type_info: dict):
    """Parse a string value according to its type."""
    value_str = value_str.strip()
    
    # Null/empty
    if value_str in ("_", "null", "None", ""):
        return type_info.get("default")
    
    category = type_info["category"]
    type_name = type_info["name"]
    
    if category == "numeric":
        if type_name == "Int":
            return int(float(value_str))
        return float(value_str)
    
    if category == "primitive":
        if type_name == "Bool":
            return value_str.lower() in ("true", "1", "yes")
        # String/Name/Text — strip quotes
        return value_str.strip('"').strip("'")
    
    if type_name == "Vector":
        return _parse_vector(value_str)
    
    if type_name == "Rotator":
        return _parse_rotator(value_str)
    
    if type_name == "Color":
        return _parse_color(value_str)
    
    if category == "asset":
        return value_str.strip('"').strip("'")
    
    if category == "enum":
        return value_str.strip('"').strip("'")
    
    if category == "array":
        return _parse_array(value_str, type_info.get("element_type", {}))
    
    if category == "struct":
        # Simple struct: {val1,val2,val3}
        return value_str
    
    # Fallback
    return value_str.strip('"')


def _parse_vector(s):
    s = s.strip().strip("()")
    parts = [float(x.strip()) for x in s.split(",")]
    if len(parts) == 3:
        return {"x": parts[0], "y": parts[1], "z": parts[2]}
    return {"x": 0, "y": 0, "z": 0}


def _parse_rotator(s):
    s = s.strip().strip("()")
    parts = [float(x.strip()) for x in s.split(",")]
    if len(parts) == 3:
        return {"pitch": parts[0], "yaw": parts[1], "roll": parts[2]}
    return {"pitch": 0, "yaw": 0, "roll": 0}


def _parse_color(s):
    s = s.strip().strip("()")
    parts = [float(x.strip()) for x in s.split(",")]
    if len(parts) == 4:
        return {"r": parts[0], "g": parts[1], "b": parts[2], "a": parts[3]}
    if len(parts) == 3:
        return {"r": parts[0], "g": parts[1], "b": parts[2], "a": 1.0}
    return {"r": 1, "g": 1, "b": 1, "a": 1}


def _parse_array(s, element_type):
    s = s.strip().strip("[]")
    if not s:
        return []
    # Simple split — doesn't handle nested arrays or quoted commas
    parts = [p.strip() for p in s.split(",")]
    return [parse_value(p, element_type) for p in parts]


def get_stats():
    return {
        "basic_types": len(COLUMN_TYPES),
        "asset_subtypes": len(ASSET_SUBTYPES),
        "aliases": len(ALIASES),
    }
