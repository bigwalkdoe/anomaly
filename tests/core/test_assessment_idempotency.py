from __future__ import annotations


def test_hash_idempotency_key_is_stable_sha256():
    from anomaly_core.assessment_idempotency import hash_idempotency_key

    digest = hash_idempotency_key("client-key")

    assert len(digest) == 64
    assert digest == "8eb943e7040b69a94bf39562088223755bff4c2e7c5fc257f1e08f870fe01d35"


def test_normalize_idempotency_key_rejects_blank_and_oversized():
    import pytest
    from anomaly_core.assessment_idempotency import (
        MAX_IDEMPOTENCY_KEY_LENGTH,
        InvalidIdempotencyKey,
        normalize_idempotency_key,
    )

    assert normalize_idempotency_key(None) is None
    assert normalize_idempotency_key("  key-1  ") == "key-1"
    with pytest.raises(InvalidIdempotencyKey):
        normalize_idempotency_key("   ")
    with pytest.raises(InvalidIdempotencyKey):
        normalize_idempotency_key("x" * (MAX_IDEMPOTENCY_KEY_LENGTH + 1))


def test_run_model_exposes_idempotency_hash():
    from anomaly_core.models import Run

    assert hasattr(Run, "idempotency_key_hash")
