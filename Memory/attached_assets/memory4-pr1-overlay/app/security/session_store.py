import os, time, logging
try:
    import redis  # type: ignore
except Exception:
    redis = None

log = logging.getLogger(__name__)

TTL_SECONDS = 600
_PREFIX = "memapp:verified:"
REDIS_URL = os.getenv("REDIS_URL", "").strip()

class _Mem:
    def __init__(self): self.m = {}
    def mark(self, phone): self.m[phone] = time.time() + TTL_SECONDS
    def ok(self, phone):
        exp = self.m.get(phone); now=time.time()
        if not exp or exp < now: self.m.pop(phone, None); return False
        return True
    def clear(self, phone): self.m.pop(phone, None)

class _Redis:
    def __init__(self, url):
        self.r = redis.Redis.from_url(url, decode_responses=True)
        try: self.r.ping()
        except Exception: raise
    def mark(self, phone): self.r.setex(_PREFIX+phone, TTL_SECONDS, "1")
    def ok(self, phone): return self.r.get(_PREFIX+phone) == "1"
    def clear(self, phone): self.r.delete(_PREFIX+phone)

_store = None
if REDIS_URL and redis is not None:
    try:
        _store = _Redis(REDIS_URL)
        log.info("Session store: Redis")
    except Exception:
        log.warning("Redis not available; using memory")
        _store = _Mem()
else:
    _store = _Mem()

def mark_verified(phone: str): _store.mark(phone)
def is_verified(phone: str) -> bool: return _store.ok(phone)
def clear_verified(phone: str): _store.clear(phone)
