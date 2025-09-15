import json, hashlib
from pathlib import Path
from typing import Optional

BASE = Path('memory-system') / 'users'

def _meta_path(phone: str) -> Path:
    d = BASE / phone
    d.mkdir(parents=True, exist_ok=True)
    return d / 'meta.json'

def _hash(p: str) -> str:
    return hashlib.sha256(p.strip().lower().encode('utf-8')).hexdigest()

def enroll(phone: str, passphrase: str) -> None:
    m = _meta_path(phone)
    data = {}
    if m.exists():
        try: data = json.loads(m.read_text(encoding='utf-8'))
        except Exception: data = {}
    data.setdefault('voice', {})['passphrase_hash'] = _hash(passphrase)
    m.write_text(json.dumps(data, indent=2), encoding='utf-8')

def verify(phone: str, passphrase: str) -> bool:
    m = _meta_path(phone)
    if not m.exists(): return False
    try: data = json.loads(m.read_text(encoding='utf-8'))
    except Exception: return False
    expected = data.get('voice', {}).get('passphrase_hash')
    return bool(expected and expected == _hash(passphrase))
