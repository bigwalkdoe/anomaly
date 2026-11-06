from __future__ import annotations

import pytest
from anomaly_core.auth import hash_password
from anomaly_core.models import APIKey, User


@pytest.mark.asyncio
async def test_create_api_key(db_session):
    user = User(email="u@example.com", name="U", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    key = APIKey(user_id=user.id, key_hash="hash", name="test")
    db_session.add(key)
    await db_session.commit()
    assert key.id is not None
