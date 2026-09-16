from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_spec_kit_skill_set_is_present_and_safe():
    required = {
        "speckit",
        "speckit-specify",
        "speckit-clarify",
        "speckit-plan",
        "speckit-checklist",
        "speckit-tasks",
        "speckit-analyze",
        "speckit-implement",
        "speckit-converge",
    }
    skills_root = ROOT / ".agents" / "skills"
    found = {
        path.parent.name
        for path in skills_root.glob("speckit*/SKILL.md")
        if path.is_file()
    }
    assert required <= found

    constitution = (ROOT / ".specify" / "memory" / "constitution.md").read_text(
        encoding="utf-8"
    )
    workflow = (skills_root / "speckit" / "SKILL.md").read_text(encoding="utf-8")

    assert "One authoritative agent runtime" in constitution
    assert "Least privilege for agents" in constitution
    assert "external" in workflow.lower()
    assert "arbitrary shell" in workflow.lower()
    assert "Do not claim" in workflow


def test_spec_kit_does_not_replace_sona_runtime():
    workflow = (
        ROOT / ".agents" / "skills" / "speckit" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "SØNA runtime remains authoritative" in workflow
    assert "production agent" in workflow
