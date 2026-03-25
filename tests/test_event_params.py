"""Test custom event parameters: AddCash(Amount:Float), SpendCash(Cost:Float)."""
import socket, json, time

def cmd(command, **params):
    s = socket.socket(); s.settimeout(15)
    s.connect(('localhost', 13377))
    s.sendall(json.dumps({"command": command, "params": params}).encode() + b'\n')
    data = b''
    while b'\n' not in data:
        chunk = s.recv(65536)
        if not chunk: break
        data += chunk
    s.close()
    return json.loads(data.decode().strip())

print("=" * 60)
print("TEST: Custom Event Parameters")
print("=" * 60)

# Create BP with Cash variable
cmd("delete_blueprint", name="BP_EventParamTest")
time.sleep(0.3)
r = cmd("create_blueprint", name="BP_EventParamTest", parent_class="Actor", variables=[
    {"name": "Cash", "type": "Float", "default": "1000"},
])
print(f"Created: {r.get('status')}")

# Skeleton compile for variables
r = cmd("compile_blueprint", name="BP_EventParamTest")
print(f"Skeleton compile: {r.get('data',{}).get('compiled')}")

# Add nodes — CustomEvent with typed params
r = cmd("add_nodes_batch", blueprint="BP_EventParamTest", nodes=[
    # CustomEvent with Float parameter "Amount" — using array format for params
    {"id": "add_cash_event", "type": "CustomEvent", "event": "AddCash",
     "params": [{"name": "Amount", "type": "Float"}]},
    # CustomEvent with Float parameter "Cost"
    {"id": "spend_cash_event", "type": "CustomEvent", "event": "SpendCash",
     "params": [{"name": "Cost", "type": "Float"}]},
    # AddCash: get cash → add amount → set cash → get cash (for print) → print
    {"id": "get_cash1", "type": "VariableGet", "variable": "Cash"},
    {"id": "add_math", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "set_cash1", "type": "VariableSet", "variable": "Cash"},
    {"id": "get_cash1b", "type": "VariableGet", "variable": "Cash"},
    {"id": "conv1", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat1", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_add", "type": "PrintString"},
    # SpendCash: get cash → compare cost → branch → subtract/set → get cash → print
    {"id": "get_cash2", "type": "GetVar", "params": {"Variable": "Cash"}},
    {"id": "ge_check", "type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
    {"id": "branch_afford", "type": "Branch"},
    {"id": "sub_math", "type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
    {"id": "set_cash2", "type": "SetVar", "params": {"Variable": "Cash"}},
    {"id": "get_cash2b", "type": "GetVar", "params": {"Variable": "Cash"}},
    {"id": "conv2", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat2", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_spend", "type": "PrintString"},
    {"id": "print_noafford", "type": "PrintString", "params": {"InString": "Cannot afford!"}},
    # BeginPlay: print init, then call AddCash(500), then call SpendCash(200)
    {"id": "print_init", "type": "PrintString", "params": {"InString": "EventParamTest: Cash=1000"}},
])
d = r.get("data", {})
print(f"Nodes: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"  Error: {e}")

# Check what pins the AddCash event has
r = cmd("get_blueprint_details", blueprint="BP_EventParamTest")
for node in r.get("data", {}).get("nodes", []):
    if "AddCash" in node.get("title", "") or "SpendCash" in node.get("title", ""):
        print(f"\n  {node.get('title')} pins:")
        for pin in node.get("pins", []):
            if not pin.get("hidden"):
                print(f"    {pin.get('direction'):6} {pin.get('name'):15} type={pin.get('type')}")

# Wire connections
r = cmd("add_connections_batch", blueprint="BP_EventParamTest", connections=[
    # BeginPlay → print init
    {"from_node": "node_0", "from_pin": "then", "to_node": "print_init", "to_pin": "execute"},

    # AddCash: event → set_cash → print (use separate GetVar for print value)
    {"from_node": "add_cash_event", "from_pin": "then", "to_node": "set_cash1", "to_pin": "execute"},
    {"from_node": "get_cash1", "from_pin": "Cash", "to_node": "add_math", "to_pin": "A"},
    {"from_node": "add_cash_event", "from_pin": "Amount", "to_node": "add_math", "to_pin": "B"},
    {"from_node": "add_math", "from_pin": "ReturnValue", "to_node": "set_cash1", "to_pin": "Cash"},
    {"from_node": "set_cash1", "from_pin": "then", "to_node": "print_add", "to_pin": "execute"},
    {"from_node": "get_cash1b", "from_pin": "Cash", "to_node": "conv1", "to_pin": "InDouble"},
    {"from_node": "conv1", "from_pin": "ReturnValue", "to_node": "concat1", "to_pin": "B"},
    {"from_node": "concat1", "from_pin": "ReturnValue", "to_node": "print_add", "to_pin": "InString"},

    # SpendCash: event → branch → subtract/set → print (use separate GetVar)
    {"from_node": "spend_cash_event", "from_pin": "then", "to_node": "branch_afford", "to_pin": "execute"},
    {"from_node": "get_cash2", "from_pin": "Cash", "to_node": "ge_check", "to_pin": "A"},
    {"from_node": "spend_cash_event", "from_pin": "Cost", "to_node": "ge_check", "to_pin": "B"},
    {"from_node": "ge_check", "from_pin": "ReturnValue", "to_node": "branch_afford", "to_pin": "Condition"},
    {"from_node": "branch_afford", "from_pin": "True", "to_node": "set_cash2", "to_pin": "execute"},
    {"from_node": "get_cash2", "from_pin": "Cash", "to_node": "sub_math", "to_pin": "A"},
    {"from_node": "spend_cash_event", "from_pin": "Cost", "to_node": "sub_math", "to_pin": "B"},
    {"from_node": "sub_math", "from_pin": "ReturnValue", "to_node": "set_cash2", "to_pin": "Cash"},
    {"from_node": "set_cash2", "from_pin": "then", "to_node": "print_spend", "to_pin": "execute"},
    {"from_node": "get_cash2b", "from_pin": "Cash", "to_node": "conv2", "to_pin": "InDouble"},
    {"from_node": "conv2", "from_pin": "ReturnValue", "to_node": "concat2", "to_pin": "B"},
    {"from_node": "concat2", "from_pin": "ReturnValue", "to_node": "print_spend", "to_pin": "InString"},
    {"from_node": "branch_afford", "from_pin": "False", "to_node": "print_noafford", "to_pin": "execute"},
])
d = r.get("data", {})
print(f"\nConnections: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"  CONN ERR: {e}")

# Set string prefixes
cmd("set_node_param", blueprint="BP_EventParamTest", node_id="concat1",
    pin_name="A", value="Cash after add: ")
cmd("set_node_param", blueprint="BP_EventParamTest", node_id="concat2",
    pin_name="A", value="Cash after spend: ")

# Final compile
r = cmd("compile_blueprint", name="BP_EventParamTest")
d = r.get("data", {})
print(f"\nCompiled: {d.get('compiled')}, errors: {len(d.get('messages',[]))}")
for m in d.get("messages", []):
    if "error" in str(m).lower():
        print(f"  {m}")

# Verify graph
r = cmd("get_blueprint_details", blueprint="BP_EventParamTest")
d = r.get("data", {})
print(f"Graph: {d.get('node_count')} nodes, {d.get('connection_count')} connections")

# Spawn and PIE
cmd("delete_actor", label="EventParamTest")
cmd("spawn_actor_at", label="EventParamTest", x=0, y=800, z=50,
    **{"class": "/Game/Arcwright/Generated/BP_EventParamTest.BP_EventParamTest_C"})
cmd("save_all")

print("\nPIE test...")
cmd("play_in_editor")
started = False
for i in range(20):
    time.sleep(0.5)
    r = cmd("is_playing")
    if r.get("data", {}).get("playing"):
        started = True
        break

if started:
    time.sleep(3)
    r = cmd("get_output_log", lines=100)
    msgs = [str(l) for l in r.get("data", {}).get("lines", [])
            if "EventParamTest" in str(l) or "Cash" in str(l) or "afford" in str(l)]
    print(f"PIE messages ({len(msgs)}):")
    for m in msgs:
        print(f"  {m[:120]}")
    cmd("stop_play")
else:
    print("PIE did not start!")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
