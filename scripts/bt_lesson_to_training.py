"""
bt_lesson_to_training.py
------------------------
Converts BT lesson files into JSONL training format for the BT LoRA adapter.
Uses the BT-specific system prompt (not the Blueprint system prompt).

Field mapping: instruction -> user message, expected_dsl -> assistant response.

Usage:
    python scripts/bt_lesson_to_training.py --lesson lessons/bt_lesson_01.json --output datasets/bt_train.jsonl
    python scripts/bt_lesson_to_training.py --lesson-dir lessons/ --output datasets/bt_train.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def generate_bt_variations(instruction: str) -> list[str]:
    """Generate natural variations of a BT instruction for training diversity."""
    variations = [instruction]

    # Casual version
    casual = instruction.lower()
    casual = casual.replace("create a behavior tree", "make a bt")
    casual = casual.replace("behavior tree", "bt")
    casual = casual.replace("blackboard key", "bb key")
    casual = casual.replace("blackboard", "bb")
    casual = casual.replace("the ai ", "ai ")
    casual = casual.replace("where the ai", "where ai")
    casual = casual.replace("seconds", "sec")
    casual = casual.replace("acceptable radius", "radius")
    casual = casual.strip()
    if casual != instruction.lower():
        variations.append(casual)

    # Technical version
    technical = instruction
    technical = technical.replace("chases", "uses MoveTo toward")
    technical = technical.replace("waits", "uses Wait for")
    technical = technical.replace("attacks", "applies damage to")
    technical = technical.replace("patrols", "loops MoveTo + Wait to")
    if technical != instruction:
        variations.append(technical)

    return variations


def bt_lesson_to_training(lesson_path: str, output_path: str, append: bool = True):
    """Convert a BT lesson file into JSONL training entries."""
    with open(lesson_path, encoding="utf-8") as f:
        lesson = json.load(f)

    entries = []
    for prompt in lesson["prompts"]:
        variations = generate_bt_variations(prompt["instruction"])

        for var_instruction in variations:
            entry = {
                "instruction": var_instruction,
                "output": prompt.get("expected_dsl") or prompt.get("expected_output", ""),
                "source": f"bt_lesson:{lesson['lesson_id']}:{prompt['id']}",
                "category": prompt["category"],
            }
            entries.append(entry)

    mode = "a" if append else "w"
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, mode, encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Wrote {len(entries)} BT training entries from {lesson['lesson_id']} to {output}")
    print(f"  ({len(lesson['prompts'])} prompts x ~{len(entries)//max(len(lesson['prompts']),1)} variations each)")
    return entries


def main():
    parser = argparse.ArgumentParser(description="Convert BT lessons to training data")
    parser.add_argument("--lesson", type=str, help="Single BT lesson file")
    parser.add_argument("--lesson-dir", type=str, help="Directory of lesson files (bt_lesson_*.json)")
    parser.add_argument("--output", default="datasets/bt_train.jsonl", help="Output JSONL path")
    parser.add_argument("--no-append", action="store_true", help="Overwrite instead of append")
    args = parser.parse_args()

    if args.lesson:
        bt_lesson_to_training(args.lesson, args.output, append=not args.no_append)
    elif args.lesson_dir:
        lesson_dir = Path(args.lesson_dir)
        if args.no_append:
            Path(args.output).write_text("")
        lesson_files = sorted(lesson_dir.glob("bt_lesson_*.json"))
        for lf in lesson_files:
            bt_lesson_to_training(str(lf), args.output, append=True)
    else:
        print("Specify --lesson or --lesson-dir")


if __name__ == "__main__":
    main()
