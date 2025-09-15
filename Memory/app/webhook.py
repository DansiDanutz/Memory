import os, logging, uuid, json
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from .branding import WELCOME
from .memory.storage import MemoryStorage
from .memory.search_v2 import search_contact
from .security.session_store import is_verified, mark_verified, cleanup_expired, session_time_remaining
from .voice.guard_simple import enroll as enroll_pass, verify as verify_pass
from .voice.azure_voice import transcribe_wav, synthesize_to_file
from .voice.whatsapp_media import download_media, ogg_opus_to_wav, upload_audio, send_audio, send_text
from .memory.classifier import MessageClassifier
# PR-2 imports
from .tenancy.rbac import whoami as whoami_user, can_search, can_perform
from .tenancy.model import TENANCY
from .memory.search_multi import search_many
from .audit import audit_event, get_user_audit_logs

router = APIRouter()

ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN','')
PHONE_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID','')
VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN','')

log = logging.getLogger(__name__)
store = MemoryStorage()
classifier = MessageClassifier()

@router.get('/webhook/whatsapp', response_class=PlainTextResponse)
async def verify(request: Request):
    p = dict(request.query_params)
    if p.get('hub.mode') == 'subscribe' and p.get('hub.verify_token') == VERIFY_TOKEN:
        return PlainTextResponse(p.get('hub.challenge',''), status_code=200)
    return PlainTextResponse('verification failed', status_code=403)

def _allowed_self(phone: str) -> List[str]:
    base = ['GENERAL','CHRONOLOGICAL','CONFIDENTIAL']
    if is_verified(phone):
        base += ['SECRET']  # ULTRA_SECRET is never exposed via search API except self-scope (and also gated in search_v2)
    return base

@router.post('/webhook/whatsapp')
async def inbound(request: Request):
    body = await request.json()
    try:
        for entry in body.get('entry', []):
            for ch in entry.get('changes', []):
                value = ch.get('value', {})
                for msg in value.get('messages', []):
                    mtype = msg.get('type'); frm = msg.get('from')
                    if not frm: 
                        continue
                    # first-contact welcome
                    user_dir = store.contacts / frm
                    if not user_dir.exists():
                        store._user_dir(frm)
                        send_text(frm, WELCOME, PHONE_ID, ACCESS_TOKEN)

                    if mtype == 'text':
                        text = msg.get('text',{}).get('body','').strip()
                        low = text.lower()

                        # Help command
                        if low.strip() == 'help:' or low.strip() == 'help':
                            help_text = """📚 Available Commands:
• help: - Show this menu
• search: <query> - Search your memories
• recent: [count] - Show recent memories
• stats: - Display memory statistics
• delete: <id> - Delete a memory
• clear: - Clear current session
• voice: - Voice enrollment guide
• login: - Login with voice
• logout: - Logout session
• export: - Export your memories
• backup: - Create backup
• restore: - Restore from backup
• category: <name> - List by category
• settings: - View/update settings
• profile: - View your profile
• whoami - Show tenant/role info
• audit: - View audit logs
• enroll: <pass> - Set passphrase
• verify: <pass> - Unlock secrets

Dept/Tenant search (if authorized):
• search dept: <query>
• search tenant: <query>"""
                            send_text(frm, help_text, PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Business controls
                        if low.strip() == 'whoami':
                            u = whoami_user(frm)
                            if not u:
                                send_text(frm, "You are not assigned to any business tenant.", PHONE_ID, ACCESS_TOKEN)
                            else:
                                send_text(frm, f"Role: {u.get('role')} | Tenant: {u.get('tenant_id')} | Department: {u.get('department')}", PHONE_ID, ACCESS_TOKEN)
                            continue

                        if low.startswith("search dept:") or low.startswith("search department:"):
                            q = text.split(":",1)[1].strip()
                            ok, role = can_search(frm, "department")
                            if not ok:
                                send_text(frm, "You do not have permission for department search.", PHONE_ID, ACCESS_TOKEN)
                            else:
                                phones = TENANCY.phones_in_department(frm)
                                cats = ['GENERAL','CHRONOLOGICAL','CONFIDENTIAL']  # cross-scope: no secret tiers
                                hits = search_many('memory-system', frm, phones, q, allowed_categories=cats, scope='department')
                                if not hits:
                                    send_text(frm, f"No department matches for: {q}", PHONE_ID, ACCESS_TOKEN)
                                else:
                                    lines = [f"- {h['phone']} [{h['category']}] {h['heading']}" for h in hits[:7]]
                                    send_text(frm, "Dept matches:\n" + "\n".join(lines), PHONE_ID, ACCESS_TOKEN)
                                audit_event("search_dept", actor=frm, query=q, hits=len(hits))
                            continue

                        if low.startswith("search tenant:"):
                            q = text.split(":",1)[1].strip()
                            ok, role = can_search(frm, "tenant")
                            if not ok:
                                send_text(frm, "You do not have permission for tenant search.", PHONE_ID, ACCESS_TOKEN)
                            else:
                                phones = TENANCY.phones_in_tenant(frm)
                                cats = ['GENERAL','CHRONOLOGICAL','CONFIDENTIAL']
                                hits = search_many('memory-system', frm, phones, q, allowed_categories=cats, scope='tenant')
                                if not hits:
                                    send_text(frm, f"No tenant matches for: {q}", PHONE_ID, ACCESS_TOKEN)
                                else:
                                    lines = [f"- {h['phone']} [{h['category']}] {h['heading']}" for h in hits[:10]]
                                    send_text(frm, "Tenant matches:\n" + "\n".join(lines), PHONE_ID, ACCESS_TOKEN)
                                audit_event("search_tenant", actor=frm, query=q, hits=len(hits))
                            continue

                        # Security commands
                        if low.startswith('enroll:') or low.startswith('set passphrase:'):
                            phrase = text.split(':',1)[1].strip()
                            enroll_pass(frm, phrase)
                            send_text(frm, 'Passphrase enrolled. Say or type: "verify: <passphrase>" to unlock secret tiers for 10 minutes.', PHONE_ID, ACCESS_TOKEN)
                            continue

                        if low.startswith('verify:') or low.startswith('passphrase:'):
                            phrase = text.split(':',1)[1].strip()
                            if verify_pass(frm, phrase):
                                mark_verified(frm)
                                send_text(frm, 'Verified. Secret tiers unlocked for 10 minutes.', PHONE_ID, ACCESS_TOKEN)
                            else:
                                send_text(frm, 'Verification failed. Try again or re-enroll.', PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Recent memories command
                        if low.startswith('recent:') or low.strip() == 'recent':
                            count = 5  # default
                            if ':' in low:
                                try:
                                    count = int(text.split(':',1)[1].strip())
                                    count = min(20, max(1, count))  # limit 1-20
                                except:
                                    count = 5
                            
                            user_dir = store.contacts / frm
                            idx_file = user_dir / 'index.json'
                            if idx_file.exists():
                                data = json.loads(idx_file.read_text(encoding='utf-8'))
                                memories = data.get('memories', [])
                                recent = sorted(memories, key=lambda x: x['timestamp'], reverse=True)[:count]
                                if recent:
                                    lines = [f"- [{m['category']}] {m['content_preview'][:50]}..." for m in recent]
                                    send_text(frm, f"Recent {count} memories:\n" + '\n'.join(lines), PHONE_ID, ACCESS_TOKEN)
                                else:
                                    send_text(frm, "No memories found.", PHONE_ID, ACCESS_TOKEN)
                            else:
                                send_text(frm, "No memories found.", PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Stats command
                        if low.strip() == 'stats:' or low.strip() == 'stats':
                            user_dir = store.contacts / frm
                            idx_file = user_dir / 'index.json'
                            if idx_file.exists():
                                data = json.loads(idx_file.read_text(encoding='utf-8'))
                                stats = data.get('stats', {})
                                by_cat = stats.get('by_category', {})
                                stats_text = f"""📊 Memory Statistics:
• Total: {stats.get('total', 0)}
• First: {stats.get('first_memory', 'N/A')[:10]}
• Last: {stats.get('last_memory', 'N/A')[:10]}

By Category:
• GENERAL: {by_cat.get('GENERAL', 0)}
• CHRONOLOGICAL: {by_cat.get('CHRONOLOGICAL', 0)}
• CONFIDENTIAL: {by_cat.get('CONFIDENTIAL', 0)}
• SECRET: {by_cat.get('SECRET', 0)}
• ULTRA_SECRET: {by_cat.get('ULTRA_SECRET', 0)}"""
                                send_text(frm, stats_text, PHONE_ID, ACCESS_TOKEN)
                            else:
                                send_text(frm, "No statistics available.", PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Delete memory command
                        if low.startswith('delete:'):
                            if not can_perform(frm, 'memory.delete'):
                                send_text(frm, "You don't have permission to delete memories.", PHONE_ID, ACCESS_TOKEN)
                                continue
                            
                            mid = text.split(':',1)[1].strip()
                            # TODO: Implement delete logic
                            send_text(frm, f"Delete functionality for ID '{mid}' is pending implementation.", PHONE_ID, ACCESS_TOKEN)
                            audit_event("delete_attempt", actor=frm, memory_id=mid)
                            continue

                        # Clear session command
                        if low.strip() == 'clear:' or low.strip() == 'clear':
                            cleanup_expired()
                            send_text(frm, "Session cleared. Locked categories require re-verification.", PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Voice instructions
                        if low.strip() == 'voice:' or low.strip() == 'voice':
                            voice_help = """🎤 Voice Setup:
1. Set passphrase: 'enroll: <your phrase>'
2. Verify by text: 'verify: <your phrase>'
3. Or send voice note saying:
   - "My passphrase is <phrase>"
   - "Verify: <phrase>"

Voice unlocks SECRET tiers for 10 min."""
                            send_text(frm, voice_help, PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Login command (voice)
                        if low.strip() == 'login:' or low.strip() == 'login':
                            send_text(frm, "To login: Send voice note with your passphrase or type 'verify: <passphrase>'", PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Logout command
                        if low.strip() == 'logout:' or low.strip() == 'logout':
                            cleanup_expired()
                            send_text(frm, "Logged out. Secret tiers now locked.", PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Export command
                        if low.strip() == 'export:' or low.strip() == 'export':
                            if not can_perform(frm, 'memory.export'):
                                send_text(frm, "You don't have permission to export memories.", PHONE_ID, ACCESS_TOKEN)
                                continue
                            send_text(frm, "Export functionality is pending implementation. Your memories are stored in Markdown format.", PHONE_ID, ACCESS_TOKEN)
                            audit_event("export_attempt", actor=frm)
                            continue

                        # Backup command
                        if low.strip() == 'backup:' or low.strip() == 'backup':
                            if not can_perform(frm, 'memory.backup'):
                                send_text(frm, "You don't have permission to create backups.", PHONE_ID, ACCESS_TOKEN)
                                continue
                            # Create backup
                            backup_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                            send_text(frm, f"Backup created: {backup_id}. Use 'restore:' to restore.", PHONE_ID, ACCESS_TOKEN)
                            audit_event("backup_created", actor=frm, backup_id=backup_id)
                            continue

                        # Restore command
                        if low.startswith('restore:') or low.strip() == 'restore':
                            if not can_perform(frm, 'memory.restore'):
                                send_text(frm, "You don't have permission to restore backups.", PHONE_ID, ACCESS_TOKEN)
                                continue
                            send_text(frm, "Restore functionality is pending implementation.", PHONE_ID, ACCESS_TOKEN)
                            audit_event("restore_attempt", actor=frm)
                            continue

                        # Category listing
                        if low.startswith('category:'):
                            cat_name = text.split(':',1)[1].strip().upper()
                            if cat_name not in ['GENERAL','CHRONOLOGICAL','CONFIDENTIAL','SECRET','ULTRA_SECRET']:
                                send_text(frm, "Invalid category. Use: GENERAL, CHRONOLOGICAL, CONFIDENTIAL, SECRET, or ULTRA_SECRET", PHONE_ID, ACCESS_TOKEN)
                                continue
                            
                            if cat_name in ['SECRET','ULTRA_SECRET'] and not is_verified(frm):
                                send_text(frm, f"{cat_name} requires verification. Use 'verify: <passphrase>'", PHONE_ID, ACCESS_TOKEN)
                                continue
                            
                            # List memories from category
                            user_dir = store.contacts / frm
                            cat_file = user_dir / cat_name / f"{cat_name.lower()}.md"
                            if cat_file.exists():
                                content = cat_file.read_text(encoding='utf-8')
                                lines = content.split('\n')[:20]  # First 20 lines
                                send_text(frm, f"{cat_name} memories (preview):\n" + '\n'.join(lines), PHONE_ID, ACCESS_TOKEN)
                            else:
                                send_text(frm, f"No memories in {cat_name} category.", PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Settings command
                        if low.strip() == 'settings:' or low.strip() == 'settings':
                            remaining = session_time_remaining(frm) if is_verified(frm) else 0
                            settings_text = f"""⚙️ Current Settings:
• Phone: {frm}
• Verified: {'Yes' if is_verified(frm) else 'No'}
• Session Time: {remaining} min remaining
• Encryption: {'Enabled' if os.getenv('ENCRYPTION_MASTER_KEY') else 'Disabled'}
• Voice: Azure STT/TTS

To change passphrase: 'enroll: <new>'"""
                            send_text(frm, settings_text, PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Profile command
                        if low.strip() == 'profile:' or low.strip() == 'profile':
                            u = whoami_user(frm)
                            user_dir = store.contacts / frm
                            idx_file = user_dir / 'index.json'
                            total = 0
                            if idx_file.exists():
                                data = json.loads(idx_file.read_text(encoding='utf-8'))
                                total = data.get('stats', {}).get('total', 0)
                            
                            profile_text = f"""👤 User Profile:
• Phone: {frm}
• Total Memories: {total}
• Tenant: {u.get('tenant_id', 'None') if u else 'None'}
• Department: {u.get('department', 'None') if u else 'None'}
• Role: {u.get('role', 'None') if u else 'None'}
• Status: {'Verified' if is_verified(frm) else 'Unverified'}"""
                            send_text(frm, profile_text, PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Audit logs command
                        if low.strip() == 'audit:' or low.strip() == 'audit':
                            if not can_perform(frm, 'audit.read'):
                                send_text(frm, "You don't have permission to view audit logs.", PHONE_ID, ACCESS_TOKEN)
                                continue
                            
                            logs = get_user_audit_logs(frm, limit=5)
                            if logs:
                                lines = [f"- {log['timestamp'][:16]} {log['event']}" for log in logs]
                                send_text(frm, "Recent audit entries:\n" + '\n'.join(lines), PHONE_ID, ACCESS_TOKEN)
                            else:
                                send_text(frm, "No audit logs found.", PHONE_ID, ACCESS_TOKEN)
                            continue

                        # Self search
                        if low.startswith('search:'):
                            q = text.split(':',1)[1].strip()
                            hits = search_contact('memory-system', frm, q, _allowed_self(frm), scope='self')
                            if not hits:
                                send_text(frm, f'No matches for: {q}', PHONE_ID, ACCESS_TOKEN)
                            else:
                                lines = [f"- [{h['category']}] {h['heading']}" for h in hits[:3]]
                                send_text(frm, 'Top matches:\n' + '\n'.join(lines), PHONE_ID, ACCESS_TOKEN)
                            audit_event("search_self", actor=frm, query=q, hits=len(hits))
                            continue

                        # Store memory
                        cat = classifier.classify(text, frm)
                        await store.store(frm, text, cat)
                        send_text(frm, f'Saved to {cat}. You can "search: <query>" or send a voice note.', PHONE_ID, ACCESS_TOKEN)

                    elif mtype == 'audio':
                        media_id = msg.get('audio',{}).get('id')
                        if not media_id:
                            send_text(frm, 'No audio id found.', PHONE_ID, ACCESS_TOKEN)
                            continue
                        ogg = download_media(media_id, ACCESS_TOKEN)
                        wav = ogg_opus_to_wav(ogg)
                        transcript = transcribe_wav(wav, os.getenv('AZURE_SPEECH_KEY',''), os.getenv('AZURE_SPEECH_REGION',''))
                        if not transcript:
                            send_text(frm, "I couldn't understand the audio.", PHONE_ID, ACCESS_TOKEN)
                            continue
                        low = transcript.lower().strip()
                        if low.startswith('verify:') or low.startswith('passphrase:') or low.startswith('my passphrase is'):
                            phrase = transcript.split(':',1)[1].strip() if ':' in transcript else low.replace('my passphrase is','').strip()
                            if verify_pass(frm, phrase):
                                mark_verified(frm)
                                send_text(frm, 'Verified by voice. Secret tiers unlocked for 10 minutes.', PHONE_ID, ACCESS_TOKEN)
                            else:
                                send_text(frm, 'Voice verification failed. Please try again.', PHONE_ID, ACCESS_TOKEN)
                            continue
                        hits = search_contact('memory-system', frm, transcript, _allowed_self(frm), scope='self')
                        if hits:
                            top = hits[:3]
                            lines = [f"- [{h['category']}] {h['heading']}" for h in top]
                            answer = f"Query: {transcript}\nTop matches:\n" + '\n'.join(lines)
                        else:
                            answer = f"No matches for: {transcript}"
                        mp3 = f"/tmp/{uuid.uuid4().hex}.mp3"
                        sent_voice = False
                        if os.getenv('AZURE_SPEECH_KEY','') and synthesize_to_file(answer, mp3, os.getenv('AZURE_SPEECH_KEY',''), os.getenv('AZURE_SPEECH_REGION','')):
                            mid = upload_audio(mp3, PHONE_ID, ACCESS_TOKEN)
                            send_audio(frm, mid, PHONE_ID, ACCESS_TOKEN); sent_voice = True
                        send_text(frm, answer + ("\n(Sent voice reply)" if sent_voice else ''), PHONE_ID, ACCESS_TOKEN)
                    else:
                        send_text(frm, 'Please send text or a voice note. Media storage is disabled in this version.', PHONE_ID, ACCESS_TOKEN)
        return {'status':'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
