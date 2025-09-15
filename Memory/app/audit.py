import os, json, time
from typing import List, Dict, Optional
from datetime import datetime

AUDIT_DIR = os.getenv("AUDIT_DIR", "data/audit")
os.makedirs(AUDIT_DIR, exist_ok=True)
AUDIT_FILE = os.path.join(AUDIT_DIR, "audit.log")

def audit_event(event_type: str, **data):
    rec = {"ts_ms": int(time.time()*1000), "event": event_type}
    rec.update(data)
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass

def get_user_audit_logs(phone: str, limit: int = 10) -> List[Dict]:
    """Get audit logs for a specific user"""
    logs = []
    try:
        if os.path.exists(AUDIT_FILE):
            with open(AUDIT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line.strip())
                        if rec.get("actor") == phone:
                            rec["timestamp"] = datetime.fromtimestamp(rec["ts_ms"] / 1000).isoformat()
                            logs.append(rec)
                    except:
                        continue
        # Return most recent logs
        return sorted(logs, key=lambda x: x.get("ts_ms", 0), reverse=True)[:limit]
    except:
        return []
