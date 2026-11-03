import pytest
from anomaly_core.db import Base, engine


@pytest.mark.asyncio
async def test_engine_connects():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    assert engine is not None
