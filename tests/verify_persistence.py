
import asyncio
import os
import uuid
import time
from pathlib import Path
from jester.core.models import Event, EventType, AgentType
from jester.core.metrics import MetricsCollector

async def test_persistence():
    # Setup unique DB path to avoid locks
    unique_id = str(uuid.uuid4())[:8]
    db_path = Path(f"tests/temp_metrics_{unique_id}.db")
    
    print(f"Testing with DB: {db_path}")
    
    try:
        # 1. Simulate Process A (Generator)
        print("\n--- Process A: Writing Events ---")
        metrics_a = MetricsCollector(storage_path=db_path)
        
        event = Event(
            event_type=EventType.CODE_GENERATED,
            agent=AgentType.KING,
            payload={"code": "print('hello')", "language": "python"}
        )
        
        print(f"Process A recording event: {event.event_id}")
        metrics_a.record_event(event.to_dict())
        
        # 2. Simulate Process B (Dashboard) polling
        print("\n--- Process B: Polling Events ---")
        metrics_b = MetricsCollector(storage_path=db_path)
        
        events = metrics_b.get_new_events(last_id=0)
        print(f"Process B found {len(events)} new events")
        
        if len(events) == 1:
            e = events[0]
            print(f"Event ID match: {e['event_id'] == event.event_id}")
            print(f"Payload match: {e['payload']['code'] == 'print(\'hello\')'}")
            
            if e['event_id'] == event.event_id:
                print("\n✅ Verification SUCCESS: Event persisted and retrieved correctly.")
            else:
                print("\n❌ Verification FAILED: Event ID mismatch.")
        else:
            print(f"\n❌ Verification FAILED: Expected 1 event, found {len(events)}")

    finally:
        # Cleanup with retry
        max_retries = 3
        for i in range(max_retries):
            try:
                if db_path.exists():
                    os.remove(db_path)
                break
            except Exception as e:
                print(f"Cleanup warning (attempt {i+1}): {e}")
                time.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(test_persistence())
