"""Test for replication_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from replication_dsl.lexer import tokenize
from replication_dsl.parser import parse
from replication_dsl.validator import validate
from replication_dsl.command_generator import generate
DSL = """REPLICATION: REP_Player
@class=BP_Player
REPLICATED_PROPERTY: Health
  @type=Float
  @default=100
  @condition=OwnerOnly
  @notify=OnRep_Health
REPLICATED_PROPERTY: Score
  @type=Integer
  @default=0
RPC: Server_Fire
  @authority=Server
  @reliable=true
RPC: Multicast_Death
  @authority=NetMulticast
  @reliable=true
NET_RELEVANCY:
  @always_relevant=false
  @net_cull_distance=15000"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("properties", []))
print(f"replication_dsl: {tree['name']}, {n} properties, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
