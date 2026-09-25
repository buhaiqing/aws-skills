from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/rsi-shadow-loop.yml"


def test_workflow_is_scheduled_shadow_and_safe():
    if yaml is None:
        return
    workflow = yaml.safe_load(WORKFLOW.read_text())
    assert set(workflow.get("on", {})) == {"schedule", "workflow_dispatch"}
    assert workflow["permissions"]["contents"] == "read"
    text = WORKFLOW.read_text().lower()
    assert "real trace" in text
    assert "outcomes.jsonl" in text
    for forbidden in ("git push", "approve --approver", "auto_promote", "failure-patterns"):
        assert forbidden not in text
