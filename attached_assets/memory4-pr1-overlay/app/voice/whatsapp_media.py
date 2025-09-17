import requests, tempfile, subprocess, uuid, os
GRAPH_BASE = "https://graph.facebook.com/v20.0"

def download_media(media_id: str, access_token: str) -> bytes:
    r = requests.get(f"{GRAPH_BASE}/{media_id}", params={"access_token": access_token}, timeout=15)
    r.raise_for_status()
    media_url = r.json().get("url")
    r2 = requests.get(media_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    r2.raise_for_status()
    return r2.content

def ogg_opus_to_wav(data: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tf:
        tf.write(data); tf.flush()
        out = f"/tmp/{uuid.uuid4().hex}.wav"
        subprocess.check_call(["ffmpeg","-y","-i",tf.name,"-ar","16000","-ac","1",out],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out

def upload_audio(file_path: str, phone_number_id: str, access_token: str, mime_type: str="audio/mpeg") -> str:
    with open(file_path, "rb") as f:
        r = requests.post(f"{GRAPH_BASE}/{phone_number_id}/media",
                          headers={"Authorization": f"Bearer {access_token}"},
                          files={"file": (os.path.basename(file_path), f, mime_type)},
                          data={"type": mime_type}, timeout=30)
    r.raise_for_status()
    return r.json().get("id")

def send_audio(to: str, media_id: str, phone_number_id: str, access_token: str):
    requests.post(f"{GRAPH_BASE}/{phone_number_id}/messages",
                  headers={"Authorization": f"Bearer {access_token}"},
                  json={"messaging_product":"whatsapp","to":to,"type":"audio","audio":{"id": media_id}},
                  timeout=15)

def send_text(to: str, body: str, phone_number_id: str, access_token: str):
    requests.post(f"{GRAPH_BASE}/{phone_number_id}/messages",
                  headers={"Authorization": f"Bearer {access_token}"},
                  json={"messaging_product":"whatsapp","to":to,"type":"text","text":{"body": body[:4096],"preview_url": False}},
                  timeout=15)
