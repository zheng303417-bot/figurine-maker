"""Create distributable archives from the project source."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def archive(filename, source, items):
    with ZipFile(DIST / filename, "w", compression=ZIP_DEFLATED) as bundle:
        for item in items:
            files = sorted(item.rglob("*")) if item.is_dir() else [item]
            for path in files:
                relative = path.relative_to(source)
                if any(part in ("__pycache__", ".env", "build") or part.endswith(".egg-info") for part in relative.parts):
                    continue
                if path.is_file() and path.suffix != ".pyc":
                    bundle.write(path, relative.as_posix())
    with ZipFile(DIST / filename) as bundle:
        if bundle.testzip() or not bundle.namelist():
            raise RuntimeError(f"Invalid archive: {filename}")
        return bundle.namelist()


if __name__ == "__main__":
    DIST.mkdir(exist_ok=True)
    skill = ROOT / "skill" / "figurine-maker"
    names = archive("figurine-maker-skill.zip", skill.parent, [skill])
    assert [name for name in names if name.endswith("/SKILL.md")] == ["figurine-maker/SKILL.md"]
    archive("figurine-maker-runtime.zip", ROOT, [ROOT / name for name in (
        "runtime", "scripts", "docs", "tests", "README.md", "examples", "evidence", "skill",
    )])
    sample = ROOT / "projects" / "validated"
    if sample.exists():
        archive("figurine-maker-examples.zip", sample, [sample / name for name in (
            "cube", "open_cube", "mock_figurine", "bambu-slice", "glb-retest",
        )])
    generated = ROOT / "projects" / "triposr-local"
    if generated.exists():
        archive("figurine-maker-triposr-example.zip", ROOT / "projects", [
            generated, ROOT / "projects" / "triposr-slice-supported",
        ])
    review = ROOT / "projects" / "robot-review"
    if (review / "review.json").is_file():
        archive("figurine-maker-robot-refinement.zip", ROOT, [
            review / name for name in (
                "baseline", "final", "validated", "slice-supported", "comparison.png", "review.json",
            )
        ] + [ROOT / name for name in (
            "scripts/review_robot.py", "scripts/robot-review-report.py", "docs/ROBOT_VISUAL_REVIEW.md",
            "skill/figurine-maker/THIRD_PARTY_NOTICES.md",
            "projects/triposr-local/print/figurine.blend",
            "examples/triposr_local/front.png",
        )])
