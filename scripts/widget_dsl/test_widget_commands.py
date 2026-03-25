"""
Widget DSL v2 — TCP command test suite.
Tests the 8 new widget commands against a running UE editor.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_client"))
from blueprint_client import ArcwrightClient, BlueprintLLMError

WBP = "WBP_Test_DSL"
passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        result = fn()
        status = result.get("status", "?")
        if status == "ok":
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}: {result.get('message', status)}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1

c = ArcwrightClient()

print(f"\n{'='*50}")
print(f"  Widget TCP Command Tests")
print(f"{'='*50}\n")

# 1. Create widget blueprint
test("create_widget_blueprint", lambda: c.send_command("create_widget_blueprint", {"name": WBP}))

# 2. Add CanvasPanel as root
test("add_widget_child (CanvasPanel root)", lambda: c.send_command("add_widget_child", {
    "widget_blueprint": WBP, "widget_type": "CanvasPanel", "widget_name": "RootCanvas"}))

# 3. Add child TextBlock
test("add_widget_child (TextBlock)", lambda: c.send_command("add_widget_child", {
    "widget_blueprint": WBP, "widget_type": "TextBlock", "widget_name": "TestText",
    "parent_widget": "RootCanvas"}))

# 4. Add ProgressBar
test("add_widget_child (ProgressBar)", lambda: c.send_command("add_widget_child", {
    "widget_blueprint": WBP, "widget_type": "ProgressBar", "widget_name": "TestBar",
    "parent_widget": "RootCanvas"}))

# 4. Set widget property
test("set_widget_property (text)", lambda: c.send_command("set_widget_property", {
    "widget_blueprint": WBP, "widget_name": "TestText", "property": "text", "value": "Hello Widget DSL"}))

# 5. Set widget font
test("set_widget_font", lambda: c.send_command("set_widget_font", {
    "widget_blueprint": WBP, "widget_name": "TestText", "font_size": 24, "font_style": "Bold"}))

# 6. Set widget brush — test on an Image widget instead (ProgressBar doesn't support brush)
test("add_widget_child (Image)", lambda: c.send_command("add_widget_child", {
    "widget_blueprint": WBP, "widget_type": "Image", "widget_name": "TestImage", "parent_widget": "RootCanvas"}))
test("set_widget_brush (Color on Image)", lambda: c.send_command("set_widget_brush", {
    "widget_blueprint": WBP, "widget_name": "TestImage", "brush_type": "Color", "brush_value": "#4A9EFF"}))

# 7. Set widget binding
test("set_widget_binding", lambda: c.send_command("set_widget_binding", {
    "widget_blueprint": WBP, "widget_name": "TestBar", "property": "Percent",
    "variable_name": "TestHealth", "variable_type": "Float"}))

# 8. Create widget animation
test("create_widget_animation", lambda: c.send_command("create_widget_animation", {
    "widget_blueprint": WBP, "animation_name": "DamageAnim", "duration": 0.3}))

# 9. Preview widget
test("preview_widget", lambda: c.send_command("preview_widget", {"widget_blueprint": WBP}))

# 10. Get widget tree (verify structure)
test("get_widget_tree", lambda: c.send_command("get_widget_tree", {"widget_blueprint": WBP}))

# 11. Cleanup
test("delete_blueprint", lambda: c.send_command("delete_blueprint", {"name": WBP}))

c.close()

print(f"\n{'='*50}")
print(f"  Results: {passed}/{passed+failed} PASS")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)
