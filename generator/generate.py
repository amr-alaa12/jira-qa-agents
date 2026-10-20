"""Generate test cases from a stories file.

Usage (from the repository root):
    python generator/generate.py
    python generator/generate.py examples/stories.json --categories generator/categories.json --output generator/test_cases.json

The categories file maps each story key to one category per acceptance
criterion, for example {"SHOP-1": ["functional", "boundary"]}. Until the AI
model is plugged in, these categories are typed by hand.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

GENERATOR_DIR = Path(__file__).resolve().parent
REPO_ROOT = GENERATOR_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generator import generate_for_stories  # noqa: E402  (needs the path set above)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate test cases from user stories.")
    parser.add_argument("stories", nargs="?", default=str(REPO_ROOT / "examples" / "stories.json"),
                        help="stories JSON file (default: examples/stories.json)")
    parser.add_argument("--categories", default=str(GENERATOR_DIR / "categories.json"),
                        help="JSON file mapping story key -> list of categories (default: generator/categories.json)")
    parser.add_argument("--output", default=str(GENERATOR_DIR / "test_cases.json"),
                        help="where to write the test cases (default: generator/test_cases.json)")
    args = parser.parse_args(argv)

    try:
        stories = _load_json(args.stories, "stories")
        categories = _load_json(args.categories, "categories")
        if not isinstance(stories, list):
            raise ValueError(f"{args.stories} must contain a JSON list of stories")
        if not isinstance(categories, dict):
            raise ValueError(f"{args.categories} must contain a JSON object: story key -> list of categories")
        test_cases = generate_for_stories(stories, categories)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    output = Path(args.output)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(test_cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"Error: cannot write {output}: {error.strerror}", file=sys.stderr)
        return 1

    story_word = "story" if len(stories) == 1 else "stories"
    print(f"Wrote {len(test_cases)} test cases for {len(stories)} {story_word} to {output}")
    return 0


def _load_json(path: str, what: str) -> Any:
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise ValueError(f"The {what} file was not found: {path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"The {what} file {path} is not valid JSON (line {error.lineno}: {error.msg})") from None
    except OSError as error:
        raise ValueError(f"Cannot read the {what} file {path}: {error.strerror}") from None


if __name__ == "__main__":
    sys.exit(main())
