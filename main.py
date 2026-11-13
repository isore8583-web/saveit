import os, re, shutil, tempfile, time
from collections import defaultdict, deque
from pathlib import Path

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

MAX_MB = int(os.getenv("MAX_MB", "500"))      # taille max par fichier
RATE_LIMIT, WINDOW = int(os.getenv("RATE_LIMIT", "20")), 60  # requêtes / minute / IP

app = FastAPI(title="SaveIt")
hits = defaultdict(deque)
BASE = {"quiet": True, "no_warnings": True, "noplaylist": True, "socket_timeout": 15}


def guard(request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    now, q = time.time(), hits[ip]
    while q and now - q[0] > WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Trop de requêtes. Réessaie dans une minute.")
    q.append(now)


def clean_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://[^\s]+$", url):
        raise HTTPException(400, "Lien invalide.")
    return url


class InfoIn(BaseModel):
    url: str


@app.post("/api/info")
def info(body: InfoIn, request: Request):
    guard(request)
    url = clean_url(body.url)
    try:
        with yt_dlp.YoutubeDL({**BASE, "skip_download": True}) as ydl:
            d = ydl.extract_info(url, download=False)
    except Exception:
        raise HTTPException(422, "Impossible de lire cette vidéo. Vérifie le lien (la vidéo doit être publique).")
    heights = sorted({f["height"] for f in d.get("formats", [])
                      if f.get("height") and f.get("vcodec") not in (None, "none")}, reverse=True)
    return {
        "title": d.get("title") or "Vidéo",
        "thumbnail": d.get("thumbnail"),
        "duration": d.get("duration"),
        "uploader": d.get("uploader"),
        "qualities": [h for h in heights if h >= 144][:6],
    }


@app.get("/api/download")
def download(url: str, request: Request, tasks: BackgroundTasks, quality: str = "best"):
    guard(request)
    url = clean_url(url)
    tmp = tempfile.mkdtemp(prefix="saveit_")
    tasks.add_task(shutil.rmtree, tmp, True)
    opts = {**BASE, "outtmpl": f"{tmp}/%(title).80s.%(ext)s",
            "max_filesize": MAX_MB * 1024 * 1024, "merge_output_format": "mp4"}
    if quality == "audio":
        opts["format"] = "ba/b"
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    elif quality.isdigit():
        h = int(quality)
        opts["format"] = f"bv*[height<={h}]+ba/b[height<={h}]/b"
    else:
        opts["format"] = "bv*+ba/b"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception:
        raise HTTPException(422, "Téléchargement impossible (vidéo privée, trop lourde ou non supportée).")
    files = list(Path(tmp).iterdir())
    if not files:
        raise HTTPException(413, f"Fichier trop lourd (max {MAX_MB} Mo).")
    f = max(files, key=lambda p: p.stat().st_size)
    return FileResponse(f, filename=f.name)


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
