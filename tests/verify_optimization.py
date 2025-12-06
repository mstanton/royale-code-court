
import asyncio
import uuid
from jester.core.event_stream import EventBus
from jester.integrations.ollama_client import KingAgent
from jester.agents.jester import JesterAgent
from jester.execution.executor import CodeExecutor
from jester.core.models import GeneratedCode, ValidationResult, AgentType, ExecutionResult, ExecutionTier

# Mock Executor to control "performance"
class MockExecutor:
    def __init__(self):
        self.call_count = 0
        
    async def execute(self, code, language="python", force_tier=None, timeout=None):
        self.call_count += 1
        # Simulate improvement: First run slow, second run fast
        time_ms = 600.0 if self.call_count == 1 else 100.0
        success = True
        
        return ExecutionResult(
            success=success,
            execution_time_ms=time_ms,
            memory_usage_mb=10.0,
            error="",
            tier=ExecutionTier.REPL
        )

async def verify_loop():
    print("Starting Optimization Loop Verification...")
    
    bus = EventBus()
    king = KingAgent(bus)
    
    # We need to monkeypatch Jester's executor to control the metrics
    jester = JesterAgent(bus)
    jester.executor = MockExecutor()
    
    task = "Write a function that calculates fibonacci sequence."
    feedback_history = []
    
    # Attempt 1
    print("\n--- Attempt 1 ---")
    code_1 = await king.generate_code(task)
    print(f"Generated (Length): {len(code_1.code)}")
    
    validation_1 = await jester.validate(code_1.code)
    print(f"Validation 1: {validation_1.feedback}")
    print(f"Time: {validation_1.execution_stats['time_ms']}ms")
    
    if "SLOW" in validation_1.feedback:
        print("✅ Correctly identified slow code.")
        feedback_history.append({
            "code": code_1.code,
            "feedback": validation_1.feedback,
            "metrics": validation_1.execution_stats
        })
        
        # Attempt 2 (Optimization)
        print("\n--- Attempt 2 (With Feedback) ---")
        code_2 = await king.generate_code(task, feedback_history=feedback_history)
        
        validation_2 = await jester.validate(code_2.code)
        print(f"Validation 2: {validation_2.feedback}")
        print(f"Time: {validation_2.execution_stats['time_ms']}ms")
        
        if validation_2.execution_stats['time_ms'] < 500:
             print("✅ Optimization Successful: Code is now fast.")
        else:
             print("❌ Optimization Failed.")
             
    else:
        print("❌ Failed to identify slow code in Attempt 1.")

if __name__ == "__main__":
    asyncio.run(verify_loop())
