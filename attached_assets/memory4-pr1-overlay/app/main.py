import os, psutil
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .webhook import router as webhook_router

app = FastAPI(title="MemoApp WhatsApp Bot", version="1.0.0")
app.include_router(webhook_router)

@app.get('/')
def root(): return {'status':'ok'}

@app.get('/metrics')
def metrics(): return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get('/admin/status')
def status():
    return {
        'cpu_percent': psutil.cpu_percent(),
        'mem': psutil.virtual_memory()._asdict(),
        'pid': os.getpid()
    }
