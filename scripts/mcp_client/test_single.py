"""Run a single IR test with its own connection. Used for crash-resilient batch testing."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blueprint_client import ArcwrightClient, BlueprintLLMError

def test_one(ir_path, timeout=60.0):
    filename = os.path.basename(ir_path)
    with open(ir_path, "r") as f:
        ir = json.load(f)
    name = ir.get("metadata", {}).get("name", "Unknown")
    nodes_exp = len(ir.get("nodes", []))
    conns_exp = len(ir.get("connections", []))

    try:
        client = ArcwrightClient(timeout=timeout)
    except Exception as e:
        return {"file": filename, "status": "SKIP", "error": f"No connection: {e}"}

    try:
        # Delete existing
        try:
            client.delete_blueprint(name)
        except BlueprintLLMError:
            pass

        # Import
        result = client.import_from_ir(ir_path)
        data = result.get("data", {})
        nodes = data.get("nodes_created", 0)
        conns = data.get("connections_wired", 0)
        compiled = data.get("compiled", False)

        nodes_ok = nodes >= nodes_exp
        conns_ok = conns >= conns_exp

        if nodes_ok and conns_ok and compiled:
            status = "PASS"
        elif nodes_ok and compiled:
            status = "PARTIAL"
        else:
            status = "FAIL"

        out = {"file": filename, "name": name, "status": status,
               "nodes": f"{nodes}/{nodes_exp}", "conns": f"{conns}/{conns_exp}",
               "compiled": compiled}
        if not conns_ok:
            out["miss_conns"] = conns_exp - conns
        return out
    except Exception as e:
        return {"file": filename, "status": "CRASH", "error": str(e)}
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == "__main__":
    ir_path = sys.argv[1]
    r = test_one(ir_path)
    print(json.dumps(r))
