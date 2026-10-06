import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_parallel_writers_use_isolated_worktrees(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "Test")
    (repository / "base.txt").write_text("base", encoding="utf-8")
    _git(repository, "add", "base.txt")
    _git(repository, "commit", "-qm", "base")
    worktree_a = tmp_path / "worker-a"
    worktree_b = tmp_path / "worker-b"
    _git(repository, "worktree", "add", "-qb", "worker-a", str(worktree_a))
    _git(repository, "worktree", "add", "-qb", "worker-b", str(worktree_b))

    (worktree_a / "a.txt").write_text("worker A", encoding="utf-8")
    (worktree_b / "b.txt").write_text("worker B", encoding="utf-8")

    assert (worktree_a / "a.txt").exists()
    assert not (worktree_a / "b.txt").exists()
    assert (worktree_b / "b.txt").exists()
    assert not (worktree_b / "a.txt").exists()
    assert not (repository / "a.txt").exists()
    assert not (repository / "b.txt").exists()
