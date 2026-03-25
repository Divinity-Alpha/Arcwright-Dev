"""
Widget Tree command tests (B11).

Tests: create_widget_blueprint, add_widget_child, set_widget_property,
       get_widget_tree, remove_widget.

Requires UE Editor running with BlueprintLLM plugin (TCP 13377).

Usage:
    python scripts/mcp_client/test_widgets.py
    python scripts/mcp_client/test_widgets.py --build-hud   # also builds test HUD
"""

import sys
import os
import json
import time
import traceback

# Set up import paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from blueprint_client import ArcwrightClient, BlueprintLLMError


def run_test(name: str, fn, client: ArcwrightClient) -> bool:
    """Run a single test, return True if passed."""
    try:
        fn(client)
        print(f"  PASS  {name}")
        return True
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        return False
    except BlueprintLLMError as e:
        print(f"  FAIL  {name}: Server error: {e}")
        return False
    except Exception as e:
        print(f"  FAIL  {name}: {traceback.format_exc()}")
        return False


# ============================================================
# Individual tests
# ============================================================

def test_create_widget_blueprint(client):
    """Create a Widget Blueprint."""
    result = client.create_widget_blueprint("WBP_Test")
    assert result["status"] == "ok", f"Expected ok, got {result}"
    data = result["data"]
    assert data["name"] == "WBP_Test"
    assert data["compiled"] == True
    assert data["has_widget_tree"] == True


def test_create_duplicate_overwrites(client):
    """Creating a WBP with existing name should overwrite (delete + recreate)."""
    result = client.create_widget_blueprint("WBP_Test")
    assert result["status"] == "ok"


def test_add_canvas_panel_root(client):
    """Add a CanvasPanel as root widget."""
    result = client.add_widget_child("WBP_Test", "CanvasPanel", "RootCanvas")
    assert result["status"] == "ok"
    data = result["data"]
    assert data["widget_name"] == "RootCanvas"
    assert data["widget_type"] == "CanvasPanel"
    assert data["parent"] == "(root)"
    assert data["compiled"] == True


def test_add_text_block(client):
    """Add a TextBlock child to the canvas."""
    result = client.add_widget_child("WBP_Test", "TextBlock", "TestLabel",
                                     parent_widget="RootCanvas")
    assert result["status"] == "ok"
    data = result["data"]
    assert data["widget_name"] == "TestLabel"
    assert data["widget_type"] == "TextBlock"
    assert data["parent"] == "RootCanvas"


def test_add_progress_bar(client):
    """Add a ProgressBar child."""
    result = client.add_widget_child("WBP_Test", "ProgressBar", "TestBar",
                                     parent_widget="RootCanvas")
    assert result["status"] == "ok"
    assert result["data"]["widget_type"] == "ProgressBar"


def test_add_duplicate_name_error(client):
    """Adding a widget with an existing name should fail."""
    try:
        client.add_widget_child("WBP_Test", "TextBlock", "TestLabel",
                                parent_widget="RootCanvas")
        assert False, "Should have raised error"
    except BlueprintLLMError as e:
        assert "already exists" in str(e)


def test_add_to_non_panel_error(client):
    """Adding a child to a non-panel widget (TextBlock) should fail."""
    try:
        client.add_widget_child("WBP_Test", "Image", "BadChild",
                                parent_widget="TestLabel")
        assert False, "Should have raised error"
    except BlueprintLLMError as e:
        assert "not a panel" in str(e)


def test_set_text_property(client):
    """Set text on a TextBlock."""
    result = client.set_widget_property("WBP_Test", "TestLabel", "text", "Hello World")
    assert result["status"] == "ok"
    assert result["data"]["compiled"] == True


def test_set_font_size(client):
    """Set font_size on a TextBlock."""
    result = client.set_widget_property("WBP_Test", "TestLabel", "font_size", 24)
    assert result["status"] == "ok"


def test_set_text_color(client):
    """Set color on a TextBlock."""
    result = client.set_widget_property("WBP_Test", "TestLabel", "color",
                                        {"r": 1, "g": 1, "b": 1, "a": 1})
    assert result["status"] == "ok"


def test_set_progress_percent(client):
    """Set percent on a ProgressBar."""
    result = client.set_widget_property("WBP_Test", "TestBar", "percent", 0.75)
    assert result["status"] == "ok"


def test_set_fill_color(client):
    """Set fill_color on a ProgressBar."""
    result = client.set_widget_property("WBP_Test", "TestBar", "fill_color",
                                        {"r": 0, "g": 1, "b": 0, "a": 1})
    assert result["status"] == "ok"


def test_set_canvas_position(client):
    """Set position on a CanvasPanel slot."""
    result = client.set_widget_property("WBP_Test", "TestLabel", "position",
                                        {"x": 20, "y": 20})
    assert result["status"] == "ok"


def test_set_canvas_size(client):
    """Set size on a CanvasPanel slot."""
    result = client.set_widget_property("WBP_Test", "TestLabel", "size",
                                        {"x": 300, "y": 40})
    assert result["status"] == "ok"


def test_get_widget_tree(client):
    """Get the widget tree and verify structure."""
    result = client.get_widget_tree("WBP_Test")
    assert result["status"] == "ok"
    data = result["data"]
    assert data["has_root"] == True
    assert data["root_type"] == "CanvasPanel"
    assert data["total_widgets"] >= 3  # Canvas + TextBlock + ProgressBar
    tree = data["tree"]
    assert len(tree) >= 1  # At least root
    root = tree[0]
    assert root["name"] == "RootCanvas"
    assert "children" in root
    assert len(root["children"]) >= 2


def test_remove_widget(client):
    """Remove a widget."""
    result = client.remove_widget("WBP_Test", "TestBar")
    assert result["status"] == "ok"
    assert result["data"]["deleted"] == True
    assert result["data"]["compiled"] == True


def test_remove_widget_idempotent(client):
    """Removing a non-existent widget should succeed with deleted=false."""
    result = client.remove_widget("WBP_Test", "NonExistent")
    assert result["status"] == "ok"
    assert result["data"]["deleted"] == False


def test_unknown_widget_type_error(client):
    """Adding an unknown widget type should fail."""
    try:
        client.add_widget_child("WBP_Test", "FooBar", "BadWidget",
                                parent_widget="RootCanvas")
        assert False, "Should have raised error"
    except BlueprintLLMError as e:
        assert "Unknown widget type" in str(e)


def test_missing_wbp_error(client):
    """Operations on a non-existent WBP should fail."""
    try:
        client.get_widget_tree("WBP_DoesNotExist")
        assert False, "Should have raised error"
    except BlueprintLLMError as e:
        assert "not found" in str(e)


# ============================================================
# HUD Build Test
# ============================================================

def build_hud(client):
    """Build the WBP_GameHUD test case from the task spec."""
    print("\n--- Building WBP_GameHUD ---")

    # Create the Widget Blueprint
    r = client.create_widget_blueprint("WBP_GameHUD")
    print(f"  Created WBP_GameHUD: {r['data']['asset_path']}")

    # Root CanvasPanel
    client.add_widget_child("WBP_GameHUD", "CanvasPanel", "RootCanvas")
    print("  Added RootCanvas (CanvasPanel)")

    # ScoreLabel — top-left
    client.add_widget_child("WBP_GameHUD", "TextBlock", "ScoreLabel",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "ScoreLabel", "text", "Score: 0")
    client.set_widget_property("WBP_GameHUD", "ScoreLabel", "font_size", 24)
    client.set_widget_property("WBP_GameHUD", "ScoreLabel", "color",
                               {"r": 1, "g": 1, "b": 1, "a": 1})
    client.set_widget_property("WBP_GameHUD", "ScoreLabel", "position",
                               {"x": 20, "y": 20})
    client.set_widget_property("WBP_GameHUD", "ScoreLabel", "size",
                               {"x": 200, "y": 40})
    print("  Added ScoreLabel (TextBlock) at top-left")

    # HealthBar — top-center
    client.add_widget_child("WBP_GameHUD", "ProgressBar", "HealthBar",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "HealthBar", "percent", 1.0)
    client.set_widget_property("WBP_GameHUD", "HealthBar", "fill_color",
                               {"r": 0, "g": 1, "b": 0, "a": 1})
    # Position: top-center with anchor
    client.set_widget_property("WBP_GameHUD", "HealthBar", "anchors",
                               {"min_x": 0.5, "min_y": 0, "max_x": 0.5, "max_y": 0})
    client.set_widget_property("WBP_GameHUD", "HealthBar", "alignment",
                               {"x": 0.5, "y": 0})
    client.set_widget_property("WBP_GameHUD", "HealthBar", "position",
                               {"x": 0, "y": 40})
    client.set_widget_property("WBP_GameHUD", "HealthBar", "size",
                               {"x": 300, "y": 30})
    print("  Added HealthBar (ProgressBar) at top-center")

    # HealthLabel — above health bar
    client.add_widget_child("WBP_GameHUD", "TextBlock", "HealthLabel",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "HealthLabel", "text", "Health")
    client.set_widget_property("WBP_GameHUD", "HealthLabel", "font_size", 18)
    client.set_widget_property("WBP_GameHUD", "HealthLabel", "color",
                               {"r": 1, "g": 1, "b": 1, "a": 1})
    client.set_widget_property("WBP_GameHUD", "HealthLabel", "justification", "Center")
    client.set_widget_property("WBP_GameHUD", "HealthLabel", "anchors",
                               {"min_x": 0.5, "min_y": 0, "max_x": 0.5, "max_y": 0})
    client.set_widget_property("WBP_GameHUD", "HealthLabel", "alignment",
                               {"x": 0.5, "y": 0})
    client.set_widget_property("WBP_GameHUD", "HealthLabel", "position",
                               {"x": 0, "y": 15})
    client.set_widget_property("WBP_GameHUD", "HealthLabel", "size",
                               {"x": 300, "y": 30})
    print("  Added HealthLabel (TextBlock) above health bar")

    # MessageText — bottom-center
    client.add_widget_child("WBP_GameHUD", "TextBlock", "MessageText",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "MessageText", "text", "")
    client.set_widget_property("WBP_GameHUD", "MessageText", "font_size", 32)
    client.set_widget_property("WBP_GameHUD", "MessageText", "color",
                               {"r": 1, "g": 1, "b": 1, "a": 1})
    client.set_widget_property("WBP_GameHUD", "MessageText", "justification", "Center")
    client.set_widget_property("WBP_GameHUD", "MessageText", "anchors",
                               {"min_x": 0.5, "min_y": 1, "max_x": 0.5, "max_y": 1})
    client.set_widget_property("WBP_GameHUD", "MessageText", "alignment",
                               {"x": 0.5, "y": 1})
    client.set_widget_property("WBP_GameHUD", "MessageText", "position",
                               {"x": 0, "y": -80})
    client.set_widget_property("WBP_GameHUD", "MessageText", "size",
                               {"x": 500, "y": 50})
    print("  Added MessageText (TextBlock) at bottom-center")

    # Verify with get_widget_tree
    tree = client.get_widget_tree("WBP_GameHUD")
    data = tree["data"]
    print(f"\n  Widget Tree: {data['total_widgets']} widgets")
    print(f"  Root: {data['root_name']} ({data['root_type']})")

    def print_tree(nodes, indent=2):
        for node in nodes:
            prefix = " " * (indent + node.get("depth", 0) * 2)
            extra = ""
            if "text" in node:
                extra = f' text="{node["text"]}"'
            if "percent" in node:
                extra = f" percent={node['percent']}"
            if "font_size" in node:
                extra += f" size={node['font_size']}"
            print(f"{prefix}{node['name']} ({node['type']}){extra}")
            if "children" in node:
                print_tree(node["children"], indent)

    print_tree(data["tree"])
    print("\n  HUD build complete!")
    return True


# ============================================================
# Main
# ============================================================

def main():
    build_hud_flag = "--build-hud" in sys.argv

    print("=" * 60)
    print("BlueprintLLM Widget Tree Tests (B11)")
    print("=" * 60)

    try:
        client = ArcwrightClient()
        client.health_check()
        print("Connected to UE Command Server\n")
    except Exception as e:
        print(f"Cannot connect to UE Command Server: {e}")
        print("Is Unreal Editor running with the BlueprintLLM plugin?")
        sys.exit(1)

    tests = [
        ("create_widget_blueprint", test_create_widget_blueprint),
        ("create_duplicate_overwrites", test_create_duplicate_overwrites),
        ("add_canvas_panel_root", test_add_canvas_panel_root),
        ("add_text_block", test_add_text_block),
        ("add_progress_bar", test_add_progress_bar),
        ("add_duplicate_name_error", test_add_duplicate_name_error),
        ("add_to_non_panel_error", test_add_to_non_panel_error),
        ("set_text_property", test_set_text_property),
        ("set_font_size", test_set_font_size),
        ("set_text_color", test_set_text_color),
        ("set_progress_percent", test_set_progress_percent),
        ("set_fill_color", test_set_fill_color),
        ("set_canvas_position", test_set_canvas_position),
        ("set_canvas_size", test_set_canvas_size),
        ("get_widget_tree", test_get_widget_tree),
        ("remove_widget", test_remove_widget),
        ("remove_widget_idempotent", test_remove_widget_idempotent),
        ("unknown_widget_type_error", test_unknown_widget_type_error),
        ("missing_wbp_error", test_missing_wbp_error),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        if run_test(name, fn, client):
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{passed + failed} PASS")
    if failed > 0:
        print(f"         {failed} FAILED")
    print(f"{'=' * 60}")

    if build_hud_flag:
        try:
            build_hud(client)
        except Exception as e:
            print(f"\nHUD build failed: {e}")
            traceback.print_exc()

    # Cleanup test WBP
    try:
        client.send_command("delete_blueprint", {"name": "WBP_Test"})
    except:
        pass

    client.close()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
