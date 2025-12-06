"""
Remote Tracer Runner
Executed in the subprocess to run user code with tracing enabled.
Emits trace events to stderr as JSON lines prefixed with [TRACE].
"""

import sys
import json
import traceback
import argparse
from pathlib import Path
from .tracer import ExecutionTracer, TraceEvent

def json_encoder(obj):
    try:
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)
    except:
        return "<unserializable>"

def trace_callback(event: TraceEvent):
    """Serialize event and print to stderr"""
    # Filter: Only trace events explicitly in the user script (or <string> if exec)
    # But since we run this as a module, filename might be the temp file.
    
    try:
        payload = {
            "execution_event_type": event.event_type, # execution_event_type to avoid confusion
            "filename": event.filename,
            "lineno": event.lineno,
            "function": event.function,
            "variables": event.variables, # Already filtered to primitives
            "timestamp": event.timestamp
        }
        # Print to stderr to separate from user program stdout
        # Using a distinct prefix for easy parsing
        print(f"[TRACE] {json.dumps(payload, default=json_encoder)}", file=sys.stderr)
    except Exception:
        # Don't let trace failure kill the program
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("script_path", help="Path to the user script to execute")
    args = parser.parse_args()

    # Setup Tracer
    tracer = ExecutionTracer(trace_callback)
    tracer.local_scope_only = True
    
    script_path = Path(args.script_path).resolve()
    
    # We need to make sure imports work relative to the script
    sys.path.insert(0, str(script_path.parent))
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            code = f.read()
            
        # Compile first to catch syntax errors cleanly (though Jester usually does this)
        compiled_code = compile(code, str(script_path), 'exec')
        
        # Run with Trace
        tracer.start()
        try:
            exec(compiled_code, {'__name__': '__main__'})
        finally:
            tracer.stop()
            
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
