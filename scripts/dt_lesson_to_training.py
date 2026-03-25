"""
dt_lesson_to_training.py
------------------------
Converts DT lesson files into JSONL training format for the DT LoRA adapter.
Uses the DT-specific system prompt (not the Blueprint or BT system prompt).

Field mapping: instruction -> user message, expected_dsl -> assistant response.

Usage:
    python scripts/dt_lesson_to_training.py --lesson lessons/dt_lesson_01.json --output datasets/dt_train.jsonl
    python scripts/dt_lesson_to_training.py --lesson-dir lessons/ --output datasets/dt_train.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def generate_dt_variations(instruction: str) -> list[str]:
    """Generate natural variations of a DT instruction for training diversity."""
    variations = [instruction]

    # Casual version
    casual = instruction.lower()
    casual = casual.replace("create a data table", "make a dt")
    casual = casual.replace("data table", "dt")
    casual = casual.replace("columns for", "with")
    casual = casual.replace("each item needs", "items have")
    casual = casual.replace("each entry should have", "entries have")
    casual = casual.replace("each row is", "rows are")
    casual = casual.replace("as a float", "(float)")
    casual = casual.replace("as an integer", "(int)")
    casual = casual.replace("as a string", "(string)")
    casual = casual.replace("whether ", "")
    casual = casual.strip()
    if casual != instruction.lower():
        variations.append(casual)

    # Technical version
    technical = instruction
    technical = technical.replace("Create a data table", "Define a UDataTable")
    technical = technical.replace("Make a data table", "Define a UDataTable")
    technical = technical.replace("Build a", "Generate a")
    if technical != instruction:
        variations.append(technical)

    return variations


def dt_lesson_to_training(lesson_path: str, output_path: str, append: bool = True):
    """Convert a DT lesson file into JSONL training entries."""
    with open(lesson_path, encoding="utf-8") as f:
        lesson = json.load(f)

    entries = []
    for prompt in lesson["prompts"]:
        variations = generate_dt_variations(prompt["instruction"])

        for var_instruction in variations:
            entry = {
                "instruction": var_instruction,
                "output": prompt.get("expected_dsl") or prompt.get("expected_output", ""),
                "source": f"dt_lesson:{lesson['lesson_id']}:{prompt['id']}",
                "category": prompt["category"],
            }
            entries.append(entry)

    mode = "a" if append else "w"
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, mode, encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Wrote {len(entries)} DT training entries from {lesson['lesson_id']} to {output}")
    print(f"  ({len(lesson['prompts'])} prompts x ~{len(entries)//max(len(lesson['prompts']),1)} variations each)")
    return entries


def main():
    parser = argparse.ArgumentParser(description="Convert DT lessons to training data")
    parser.add_argument("--lesson", type=str, help="Single DT lesson file")
    parser.add_argument("--lesson-dir", type=str, help="Directory of lesson files (dt_lesson_*.json)")
    parser.add_argument("--output", default="datasets/dt_train.jsonl", help="Output JSONL path")
    parser.add_argument("--no-append", action="store_true", help="Overwrite instead of append")
    args = parser.parse_args()

    if args.lesson:
        dt_lesson_to_training(args.lesson, args.output, append=not args.no_append)
    elif args.lesson_dir:
        lesson_dir = Path(args.lesson_dir)
        if args.no_append:
            Path(args.output).write_text("")
        lesson_files = sorted(lesson_dir.glob("dt_lesson_*.json"))
        for lf in lesson_files:
            dt_lesson_to_training(str(lf), args.output, append=True)
    else:
        print("Specify --lesson or --lesson-dir")


if __name__ == "__main__":
    main()
