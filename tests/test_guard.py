import pytest
from jester.execution.tracer import ExecutionTracer
from jester.agents.guard import RoyalGuard, GuardMode, TraceEvent

def test_tracer_capture():
    """Verify tracer captures variables"""
    events = []
    def callback(e):
        events.append(e)
    
    tracer = ExecutionTracer(callback)
    
    def test_func():
        x = 10
        y = "test"
        return x + 5
        
    tracer.run_with_trace(test_func)
    
    assert len(events) > 0
    # Check for variable x=10
    found_x = False
    for e in events:
        if 'x' in e.variables and e.variables['x'] == 10:
            found_x = True
            break
    assert found_x

def test_guard_strict_loop_block():
    """Verify strict mode blocks loops"""
    guard = RoyalGuard(None, mode=GuardMode.STRICT)
    guard.MAX_LOOPS = 5 # Set low limit for test
    
    tracer = ExecutionTracer(guard.handle_trace)
    
    def infinite_loop():
        i = 0
        while i < 10: # This is 10 iterations, limit is 5
            i += 1
            
    # Should raise RuntimeError from Guard
    with pytest.raises(RuntimeError) as excinfo:
        tracer.run_with_trace(infinite_loop)
    
    assert "Guard Block" in str(excinfo.value)

def test_guard_learning_loop_allow():
    """Verify learning mode allows loops (but warns)"""
    guard = RoyalGuard(None, mode=GuardMode.LEARNING)
    guard.MAX_LOOPS = 5 # limit is 5, loop is 10
    
    tracer = ExecutionTracer(guard.handle_trace)
    
    def infinite_loop():
        i = 0
        while i < 10:
            i += 1
            
    # Should NOT raise exception, but should log violations
    tracer.run_with_trace(infinite_loop)
    
    # We can't easily check print output here, but execution finishing proves non-blocking
    assert True 
