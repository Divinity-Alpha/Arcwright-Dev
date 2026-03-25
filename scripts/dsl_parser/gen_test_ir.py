import os
from parser import parse, save_ir

dsl = """BLUEPRINT: BP_HelloWorld
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Hello World"]

EXEC n1.Then -> n2.Execute"""

result = parse(dsl)

os.makedirs("C:/Arcwright/test_ir", exist_ok=True)
save_ir(result, "C:/Arcwright/test_ir/T1_01_HelloWorld.blueprint.json")

print("Saved. Errors:", result["errors"])
print("Stats:", result["stats"])
