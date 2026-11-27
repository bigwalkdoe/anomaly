from __future__ import annotations

from types import SimpleNamespace

from anomaly_core.policy import PolicyDecision, evaluate_assessment_request
from anomaly_core.scope import ScopeCheckResult


def _approved_engagement():
    entry = SimpleNamespace(kind="in", target_value="allowed.test")
    return SimpleNamespace(status="approved", scope=SimpleNamespace(entries=[entry]))


def test_decision_metadata_for_out_of_scope_includes_scope_context():
    decision = PolicyDecision(
        allowed=False,
        reason="out_of_scope",
        metadata={"targets": ["evil.test"]},
        scope_result=ScopeCheckResult(["allowed.test"], ["evil.test"], True),
    )

    metadata = decision.to_metadata(op="assessment.request")

    assert metadata["allowed"] is False
    assert metadata["reason"] == "out_of_scope"
    assert metadata["op"] == "assessment.request"
    assert metadata["targets"] == ["evil.test"]
    assert metadata["in_scope"] == ["allowed.test"]
    assert metadata["out_of_scope"] == ["evil.test"]
    assert metadata["has_warning"] is True


def test_decision_metadata_for_unapproved_preserves_status_without_scope_context():
    original = {"status": "draft", "op": "assessment.request"}
    decision = PolicyDecision(
        allowed=False,
        reason="engagement_not_approved",
        metadata=original,
    )

    metadata = decision.to_metadata()

    assert metadata["allowed"] is False
    assert metadata["reason"] == "engagement_not_approved"
    assert metadata["status"] == "draft"
    assert metadata["op"] == "assessment.request"
    assert "out_of_scope" not in metadata
    assert original == {"status": "draft", "op": "assessment.request"}


def test_decision_metadata_for_allowed_includes_source_and_scope_context():
    decision = PolicyDecision(
        allowed=True,
        scope_result=ScopeCheckResult(["allowed.test"], [], False),
    )

    metadata = decision.to_metadata(op="assessment.request", source="api.v1")

    assert metadata["allowed"] is True
    assert metadata["reason"] is None
    assert metadata["op"] == "assessment.request"
    assert metadata["source"] == "api.v1"
    assert metadata["targets"] == []
    assert metadata["in_scope"] == ["allowed.test"]
    assert metadata["out_of_scope"] == []
    assert metadata["has_warning"] is False


def test_evaluated_decision_preserves_requested_target_order():
    decision = evaluate_assessment_request(
        _approved_engagement(), ["evil.test", "allowed.test"]
    )

    metadata = decision.to_metadata()

    assert metadata["allowed"] is False
    assert metadata["targets"] == ["evil.test", "allowed.test"]
    assert metadata["in_scope"] == ["allowed.test"]
    assert metadata["out_of_scope"] == ["evil.test"]


def test_allowed_evaluated_decision_includes_requested_targets():
    decision = evaluate_assessment_request(_approved_engagement(), ["allowed.test"])

    metadata = decision.to_metadata()

    assert metadata["allowed"] is True
    assert metadata["targets"] == ["allowed.test"]
