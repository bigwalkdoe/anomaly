import asyncio
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def my_fixture():
    loop_during_setup = asyncio.get_running_loop()
    print(f"Fixture setup loop: {loop_during_setup}")
    yield "value"
    loop_during_teardown = asyncio.get_running_loop()
    print(f"Fixture teardown loop: {loop_during_teardown}")


@pytest.mark.asyncio
async def test_loop(my_fixture):
    loop_during_test = asyncio.get_running_loop()
    print(f"Test loop: {loop_during_test}")
    assert my_fixture == "value"
