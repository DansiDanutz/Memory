from typing import List, Dict
from .search_v2 import search_contact

def search_many(base_dir: str, actor_phone: str, phones: List[str], query: str, allowed_categories: List[str], scope: str, per_contact_limit: int = 3, max_total: int = 12) -> List[Dict]:
    all_hits: List[Dict] = []
    for p in phones:
        hits = search_contact(base_dir, p, query, allowed=allowed_categories, max_hits=per_contact_limit, scope=scope)
        for h in hits:
            h2 = dict(h)
            h2["phone"] = p
            all_hits.append(h2)
    all_hits.sort(key=lambda x: x["score"], reverse=True)
    return all_hits[:max_total]
