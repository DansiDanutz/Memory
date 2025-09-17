import os, re
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from ..security.encryption import EncryptionService, ENC_PREFIX

def _read(p: Path) -> str:
    try: return p.read_text(encoding='utf-8')
    except Exception: return ''

def _segments(md: str) -> List[Tuple[str,str]]:
    segs=[]; head=''; buf=[]
    for line in md.splitlines():
        if line.startswith('## '):
            if head: segs.append((head, '\n'.join(buf)))
            head=line[3:]; buf=[]
        else:
            buf.append(line)
    if head: segs.append((head, '\n'.join(buf)))
    return segs

def search_contact(base_dir: str, phone: str, query: str, allowed: List[str], max_hits: int=6, scope: str='self') -> List[Dict]:
    root = Path(base_dir) / 'users' / phone
    hits: List[Dict] = []
    if not root.exists(): return hits
    q = query.strip().lower()
    enc = EncryptionService()

    # PR-1.1: ULTRA_SECRET only searchable with scope='self'
    if scope != 'self' and 'ULTRA_SECRET' in allowed:
        allowed = [c for c in allowed if c != 'ULTRA_SECRET']

    # map categories to files (your storage writes uppercase dir names)
    for cat in ['GENERAL','CHRONOLOGICAL','CONFIDENTIAL','SECRET','ULTRA_SECRET']:
        if cat not in allowed: continue
        if cat == 'CHRONOLOGICAL':
            # scan all md files under chronological
            cat_dir = root / cat
            if not cat_dir.exists(): continue
            for f in cat_dir.glob('*.md'):
                for head, seg in _segments(_read(f)):
                    body = _extract_body(seg)
                    if body.startswith(ENC_PREFIX):
                        body_dec = enc.decrypt(body, phone, cat) or ''
                    else:
                        body_dec = body
                    text = (head + '\n' + body_dec).lower()
                    score = sum(1 for tok in q.split() if tok in text)
                    if score>0: hits.append({'category':cat,'heading':head,'excerpt':body_dec[:240], 'score':score})
        else:
            f = root / cat / (cat.lower()+'.md')
            if not f.exists(): continue
            for head, seg in _segments(_read(f)):
                body = _extract_body(seg)
                if body.startswith(ENC_PREFIX):
                    body_dec = enc.decrypt(body, phone, cat) or ''
                else:
                    body_dec = body
                text = (head + '\n' + body_dec).lower()
                score = sum(1 for tok in q.split() if tok in text)
                if score>0: hits.append({'category':cat,'heading':head,'excerpt':body_dec[:240], 'score':score})
    hits.sort(key=lambda x: x['score'], reverse=True)
    return hits[:max_hits]

def _extract_body(seg: str) -> str:
    # Look for **Content (Encrypted):** block or **Content:**
    enc_block = re.search(r"\*\*Content \(Encrypted\):\*\*\n```\n([\s\S]*?)\n```", seg, flags=re.M)
    if enc_block: return enc_block.group(1).strip()
    plain = re.search(r"\*\*Content:\*\*\n([\s\S]*?)\n---", seg, flags=re.M)
    return plain.group(1).strip() if plain else ''
