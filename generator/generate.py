from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence

GENERATOR_DIR = Path(__file__).resolve().parent
REPO_ROOT = GENERATOR_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generator import CategoryModel, generate_for_stories, to_csv, to_excel, to_gherkin_feature, to_xray_json
from generator.classifier import LOW_CONFIDENCE, MODEL_PATH


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate test cases from user stories.")
    parser.add_argument("stories", nargs="?", default=str(REPO_ROOT / "examples" / "stories.json"),
                        help="stories JSON file (default: examples/stories.json)")
    parser.add_argument("--categories",
                        help="JSON file mapping story key -> list of categories; skips the AI model")
    parser.add_argument("--model", default=None,
                        help="trained AI model used when --categories is not given (default: self-made classifier)")
    parser.add_argument("--output", default=str(GENERATOR_DIR / "test_cases.json"),
                        help="where to write the test cases (default: generator/test_cases.json)")
    parser.add_argument("--optional", "--include-optional", action="store_true",
                        help="include optional attributes (priority, preconditions, execution_type, gherkin)")
    parser.add_argument("--deduplicate", action="store_true",
                        help="deduplicate redundant test cases across criteria")
    parser.add_argument("--format", choices=["json", "csv", "excel", "gherkin", "xray"], default="json",
                        help="output format (default: json)")
    args = parser.parse_args(argv)

    try:
        stories = _load_json(args.stories, "stories")
        if not isinstance(stories, list):
            raise ValueError(f"{args.stories} must contain a JSON list of stories")
        if args.categories:
            categories = _load_json(args.categories, "categories")
            if not isinstance(categories, dict):
                raise ValueError(f"{args.categories} must contain a JSON object: story key -> list of categories")
        else:
            categories = CategoryModel.load(args.model).categorize(stories)
            _print_predictions(stories, categories)
        test_cases = generate_for_stories(
            stories,
            categories,
            include_optional=args.optional,
            deduplicate=args.deduplicate,
        )
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    output = Path(args.output)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "json":
            output.write_text(json.dumps(test_cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        elif args.format == "csv":
            output.write_text(to_csv(test_cases), encoding="utf-8")
        elif args.format == "excel":
            to_excel(test_cases, output)
        elif args.format == "gherkin":
            feature_story = stories[0] if len(stories) == 1 else {"title": "Test Suite"}
            output.write_text(to_gherkin_feature(feature_story, test_cases), encoding="utf-8")
        elif args.format == "xray":
            output.write_text(to_xray_json(test_cases) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"Error: cannot write {output}: {error.strerror}", file=sys.stderr)
        return 1

    story_word = "story" if len(stories) == 1 else "stories"
    print(f"Wrote {len(test_cases)} test cases for {len(stories)} {story_word} in {args.format} format to {output}")
    return 0


def _print_predictions(stories: List[Any], categories: Mapping[str, Sequence[Any]]) -> None:
    for story in stories:
        for criterion, (category, confidence) in zip(story["acceptance_criteria"], categories[story["key"]]):
            note = "  <- low confidence, please check" if confidence < LOW_CONFIDENCE else ""
            print(f"{story['key']}: {criterion.strip()} -> {category} ({confidence:.2f}){note}")


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
