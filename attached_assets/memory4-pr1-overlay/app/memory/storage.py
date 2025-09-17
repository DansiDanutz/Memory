import os, json, uuid, logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..security.encryption import EncryptionService

log = logging.getLogger(__name__)

class MemoryStorage:
    def __init__(self, base_dir: str = 'memory-system'):
        self.base = Path(base_dir)
        self.users = self.base / 'users'
        self.users.mkdir(parents=True, exist_ok=True)
        self.enc = EncryptionService()

    def _user_dir(self, phone: str) -> Path:
        d = self.users / phone
        for c in ['GENERAL','CHRONOLOGICAL','CONFIDENTIAL','SECRET','ULTRA_SECRET']:
            (d / c).mkdir(parents=True, exist_ok=True)
        if not (d / 'index.json').exists():
            (d / 'index.json').write_text(json.dumps({'memories': [], 'stats': {}}, indent=2), encoding='utf-8')
        return d

    def _file_for(self, phone: str, category: str, ts: Optional[datetime]=None) -> Path:
        d = self._user_dir(phone) / category
        if category == 'CHRONOLOGICAL':
            ts = ts or datetime.utcnow()
            return d / f"{ts.strftime('%Y-%m-%d')}.md"
        return d / f"{category.lower()}.md"

    async def store(self, phone: str, content: str, category: str, ts: Optional[datetime]=None,
                    tenant_id: Optional[str]=None, department_id: Optional[str]=None) -> str:
        ts = ts or datetime.utcnow()
        mid = uuid.uuid4().hex[:8]
        path = self._file_for(phone, category, ts)

        if category in ('SECRET','ULTRA_SECRET'):
            body = await self.enc.encrypt(content, phone, category)
            body_label = "Content (Encrypted)"
        else:
            body = content
            body_label = "Content"

        entry = f"""
## {ts.strftime('%Y-%m-%d %H:%M:%S')} — [{mid}]
**Category:** {category}

**{body_label}:**
{('```\n'+body+'\n```') if body_label.endswith('(Encrypted)') else body}

---
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry)

        # Update index without leaking secrets
        self._update_index(phone, mid, category, ts, content if category not in ('SECRET','ULTRA_SECRET') else '', tenant_id, department_id)
        return mid

    def _update_index(self, phone: str, mid: str, category: str, ts: datetime, preview: str,
                      tenant_id: Optional[str], department_id: Optional[str]):
        u = self._user_dir(phone)
        idx = u / 'index.json'
        data = json.loads(idx.read_text(encoding='utf-8'))
        data.setdefault('memories', []).append({
            'id': mid,
            'category': category,
            'timestamp': ts.isoformat(),
            'content_preview': (preview[:100] if preview else ''),
            'encrypted': category in ('SECRET','ULTRA_SECRET'),
            'tenant_id': tenant_id,
            'department_id': department_id,
            'user_phone': phone
        })
        s = data.setdefault('stats', {})
        s['total'] = s.get('total', 0) + 1
        bc = s.setdefault('by_category', {})
        bc[category] = bc.get(category, 0) + 1
        s['last_memory'] = ts.isoformat()
        if 'first_memory' not in s: s['first_memory'] = ts.isoformat()
        idx.write_text(json.dumps(data, indent=2), encoding='utf-8')
