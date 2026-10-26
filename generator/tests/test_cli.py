import json
import subprocess
import sys
from pathlib import Path

from generator.generate import main

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "generator" / "generate.py"


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_script_runs_on_the_example_stories(tmp_path):
    output = tmp_path / "test_cases.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(REPO_ROOT / "examples" / "stories.json"),
         "--categories", str(REPO_ROOT / "generator" / "categories.json"), "--output", str(output)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    test_cases = json.loads(output.read_text(encoding="utf-8"))
    assert len(test_cases) >= 4  # at least 2 for each of the 2 criteria
    assert all(tc["story_key"] == "SHOP-1" for tc in test_cases)
    assert "Wrote" in result.stdout


def test_missing_categories_for_a_story_is_an_error(tmp_path, capsys):
    stories = write_json(tmp_path / "stories.json", [{"key": "A-1", "acceptance_criteria": ["x"]}])
    categories = write_json(tmp_path / "categories.json", {})
    assert main([stories, "--categories", categories, "--output", str(tmp_path / "out.json")]) == 1
    assert "No categories given for these stories: A-1" in capsys.readouterr().err
    assert not (tmp_path / "out.json").exists()


def test_missing_file_is_an_error(tmp_path, capsys):
    assert main([str(tmp_path / "nope.json"), "--output", str(tmp_path / "out.json")]) == 1
    assert "stories file was not found" in capsys.readouterr().err


def test_invalid_json_is_an_error(tmp_path, capsys):
    stories = tmp_path / "stories.json"
    stories.write_text("[{", encoding="utf-8")
    assert main([str(stories), "--output", str(tmp_path / "out.json")]) == 1
    assert "is not valid JSON" in capsys.readouterr().err


def test_wrong_top_level_shape_is_an_error(tmp_path, capsys):
    stories = write_json(tmp_path / "stories.json", {"key": "A-1"})
    assert main([stories, "--output", str(tmp_path / "out.json")]) == 1
    assert "must contain a JSON list" in capsys.readouterr().err
