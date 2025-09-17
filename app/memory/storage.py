import os, json, uuid, logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..security.encryption import EncryptionService

log = logging.getLogger(__name__)

class MemoryStorage:
    def __init__(self, base_dir: str = 'data'):
        self.base = Path(base_dir)
        self.contacts = self.base / 'contacts'
        self.contacts.mkdir(parents=True, exist_ok=True)
        self.enc = EncryptionService()

    def _user_dir(self, phone: str) -> Path:
        d = self.contacts / phone
        for c in ['GENERAL','CHRONOLOGICAL','CONFIDENTIAL','SECRET','ULTRA_SECRET']:
            (d / c).mkdir(parents=True, exist_ok=True)
        # No need for separate chronological folder - using CHRONOLOGICAL
        if not (d / 'index.json').exists():
            (d / 'index.json').write_text(json.dumps({'memories': [], 'stats': {}}, indent=2), encoding='utf-8')
        return d

    def _file_for(self, phone: str, category: str, ts: Optional[datetime]=None) -> Path:
        d = self._user_dir(phone)
        if category == 'CHRONOLOGICAL':
            ts = ts or datetime.utcnow()
            return d / 'CHRONOLOGICAL' / f"{ts.strftime('%Y-%m-%d')}.md"
        return d / category / f"{category.lower()}.md"

    async def store(self, phone: str, content: str, category: str, ts: Optional[datetime]=None,
                    tenant_id: Optional[str]=None, department_id: Optional[str]=None) -> str:
        ts = ts or datetime.utcnow()
        mid = uuid.uuid4().hex[:8]
        path = self._file_for(phone, category, ts)

        if category in ('SECRET','ULTRA_SECRET'):
            # Encrypt content - EncryptionService already adds ENC:: prefix
            body = await self.enc.encrypt(content, phone, category)
            body_label = "Content (Encrypted)"
        else:
            body = content
            body_label = "Content"

        if body_label.endswith('(Encrypted)'):
            content_block = f"```\n{body}\n```"
        else:
            content_block = body
            
        entry = f"""
## {ts.strftime('%Y-%m-%d %H:%M:%S')} — [{mid}]
**Category:** {category}

**{body_label}:**
{content_block}

---
"""
        # Write to category file
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry)
        
        # ALSO write to chronological daily file (PR-1.1 requirement)
        chrono_path = self._user_dir(phone) / 'CHRONOLOGICAL' / f"{ts.strftime('%Y-%m-%d')}.md"
        chrono_path.parent.mkdir(parents=True, exist_ok=True)
        with open(chrono_path, 'a', encoding='utf-8') as f:
            f.write(entry)

        # Update index - NEVER include content preview for SECRET/ULTRA_SECRET
        preview_text = '' if category in ('SECRET','ULTRA_SECRET') else content[:100]
        self._update_index(phone, mid, category, ts, preview_text, tenant_id, department_id)
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
