from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_single_space_publisher_and_main_guard():
    active = (ROOT / ".github/workflows/deploy-huggingface-space.yml").read_text()
    legacy = (ROOT / ".github/workflows/sync-huggingface-space.yml").read_text()
    assert "push:" not in legacy and "HF_TOKEN" not in legacy
    assert "git " not in legacy
    assert "if: github.ref == 'refs/heads/main'" in active
    assert "git archive --format=tar HEAD" in active
    assert (
        "openoperator-build.json" in active
        and '"source_sha": os.environ["SOURCE_SHA"]' in active
    )
    assert "https://huggingface.co/spaces/Leon4gr45/openoperator" in active
    assert "jules-" not in active


def test_state_preservation_and_image_runtime_constraints():
    copy = (ROOT / "docker/run/fs/ins/copy_A0.sh").read_text()
    image = (ROOT / "Dockerfile").read_text()
    assert "--exclude='/usr'" in copy
    for marker in [
        "PIP_NO_INDEX=1",
        "USER 1000:1000",
        "EXPOSE 7860",
        "A0_CLOUDFLARE_DISABLED=true",
    ]:
        assert marker in image
