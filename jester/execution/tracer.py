"""
Royal Guard - Execution Tracer
Provides realtime "bowling lane bumpers" by monitoring execution line-by-line.
"""

import sys
import time
import inspect
from typing import Callable, Any, Dict, Optional, List
from dataclasses import dataclass

@dataclass
class TraceEvent:
    event_type: str  # line, call, return, exception
    filename: str
    lineno: int
    function: str
    variables: Dict[str, Any]
    timestamp: float

class ExecutionTracer:
    """
    Hooks into sys.settrace to monitor code execution.
    Acts as the sensor for the Royal Guard.
    """
    
    def __init__(self, callback: Callable[[TraceEvent], None]):
        self.callback = callback
        self.start_time = 0.0
        self.instruction_count = 0
        self.max_instructions = 10000 # Safety brake
        self.local_scope_only = True

    def _trace_func(self, frame, event, arg):
        """Standard trace function compatible with sys.settrace"""
        self.instruction_count += 1
        current_time = time.time()
        
        # Extract variables if interesting
        variables = {}
        if event == 'line' or event == 'return':
             # Only capture primitives to avoid overhead
             for k, v in frame.f_locals.items():
                 if isinstance(v, (int, float, str, bool, type(None))):
                     variables[k] = v
                 elif hasattr(v, '__len__'):
                     try:
                        variables[f"{k}_len"] = len(v)
                     except (TypeError, AttributeError):
                        pass

        trace_event = TraceEvent(
            event_type=event,
            filename=frame.f_code.co_filename,
            lineno=frame.f_lineno,
            function=frame.f_code.co_name,
            variables=variables,
            timestamp=current_time - self.start_time
        )
        
        self.callback(trace_event)
        
        # Safety brake
        if self.instruction_count > self.max_instructions:
            raise RuntimeError("Maximum instruction limit reached (Guard Emergency Brake)")
            
        return self._trace_func

    def start(self):
        """Start tracing"""
        self.start_time = time.time()
        self.instruction_count = 0
        sys.settrace(self._trace_func)

    def stop(self):
        """Stop tracing"""
        sys.settrace(None)

    def run_with_trace(self, func: Callable, *args, **kwargs):
        """Run a function with tracing enabled"""
        self.start()
        try:
            return func(*args, **kwargs)
        finally:
            self.stop()
