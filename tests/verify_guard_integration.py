import asyncio
import pytest
from jester.core.event_stream import EventBus
from jester.agents.jester import JesterAgent
from jester.agents.guard import GuardMode

async def test_guard_blocking_in_jester():
    """Verify that JesterAgent uses the Guard to block infinite loops"""
    event_bus = EventBus()
    jester = JesterAgent(event_bus)
    
    # Configure Guard to be strict with low loop limit
    jester.guard.mode = GuardMode.STRICT
    jester.guard.MAX_LOOPS = 5
    
    # Code with infinite loop
    loop_code = """
def loop():
    i = 0
    while i < 100:
        i += 1
    return i

loop()
"""
    
    # We expect this to fail execution because the Guard will raise RuntimeError
    result = await jester.validate(loop_code, "python")
    
    print(f"Executes: {result.executes}")
    if result.execution_result:
        print(f"Error: {result.execution_result.error}")
        
    assert not result.executes
    assert "Guard Block" in str(result.execution_result.error)
    print("✅ Guard correctly blocked execution inside Jester")

if __name__ == "__main__":
    asyncio.run(test_guard_blocking_in_jester())
