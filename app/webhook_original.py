import os, logging, uuid
from typing import Dict, Any, List
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from app.memory.storage import MemoryStorage
from app.memory.search_v2 import search_contact
from app.security.session_store import is_verified, mark_verified
from app.voice.guard_simple import enroll as enroll_pass, verify as verify_pass
from app.voice.azure_voice import transcribe_wav, synthesize_to_file
from app.voice.whatsapp_media import download_media, ogg_opus_to_wav, upload_audio, send_audio, send_text
from app.memory.classifier import MessageClassifier

router = APIRouter()

ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN','')
PHONE_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID','')
VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN', os.getenv('VERIFY_TOKEN', 'memory-app-verify-2024'))

log = logging.getLogger(__name__)
store = MemoryStorage()
classifier = MessageClassifier()

@router.get('/webhook', response_class=PlainTextResponse)
async def verify(request: Request):
    p = dict(request.query_params)
    if p.get('hub.mode') == 'subscribe' and p.get('hub.verify_token') == VERIFY_TOKEN:
        return PlainTextResponse(p.get('hub.challenge',''), status_code=200)
    return PlainTextResponse('verification failed', status_code=403)

def _allowed(phone: str) -> List[str]:
    base = ['GENERAL','CHRONOLOGICAL','CONFIDENTIAL']
    if is_verified(phone):
        base += ['SECRET','ULTRA_SECRET']
    return base

@router.post('/webhook')
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
                    if mtype == 'text':
                        text = msg.get('text',{}).get('body','').strip()
                        low = text.lower()
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
                        if low.startswith('search:'):
                            q = text.split(':',1)[1].strip()
                            hits = search_contact('memory-system', frm, q, _allowed(frm))
                            if not hits:
                                send_text(frm, f'No matches for: {q}', PHONE_ID, ACCESS_TOKEN)
                            else:
                                lines = [f"- [{h['category']}] {h['heading']}" for h in hits[:3]]
                                send_text(frm, 'Top matches:\n' + '\n'.join(lines), PHONE_ID, ACCESS_TOKEN)
                            continue
                        # store memory
                        cat = await classifier.classify(text, frm) if hasattr(classifier, 'classify') else 'GENERAL'
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
                        hits = search_contact('memory-system', frm, transcript, _allowed(frm))
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
