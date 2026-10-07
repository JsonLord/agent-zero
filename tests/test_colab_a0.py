import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import colab_a0


def _repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    (path / "README").write_text("fixture", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "fixture"], check=True)


def _parse_last_json(text: str) -> dict:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return json.loads(text)


def test_colab_exec_returns_structured_passing_evidence(tmp_path, capsys):
    _repo(tmp_path)

    code = colab_a0.execute(
        tmp_path,
        [sys.executable, "-c", "print('one harmless assertion passed')"],
        timeout=5,
    )
    evidence = _parse_last_json(capsys.readouterr().out)

    assert code == 0
    assert evidence["backend"] == "colab"
    assert evidence["commit"]
    assert evidence["command"][0] == sys.executable
    assert evidence["exit_code"] == 0
    assert evidence["result"] == "PASS"
    assert "one harmless assertion passed" in evidence["stdout_tail"]
    assert "SPYNEL_AGENT_ZERO_API_KEY" not in json.dumps(evidence)


def test_colab_exec_rejects_non_checkout(tmp_path, capsys):
    code = colab_a0.execute(tmp_path, [sys.executable, "-V"], timeout=5)
    evidence = _parse_last_json(capsys.readouterr().out)
    assert code == 2
    assert evidence["result"] == "BLOCKED"
