"""Bölüm videolarını Vercel'e (karar-sende-media) yükler -> herkese açık, Instagram'ın çekebileceği adres.

  python vercel_yukle.py                 -> medya/ klasöründeki TÜM dosyaları dağıtır (değişmeyenler tekrar yüklenmez)
  python vercel_yukle.py --ekle dosya.mp4 -> dosyayı medya/ klasörüne kopyalar ve dağıtır

.env içinde şunlar olmalı (sen yazacaksın, sohbete yapıştırma):
  VERCEL_TOKEN=...            (vercel.com/account/tokens -> Create Token, kapsam: almss)
  VERCEL_TEAM_ID=team_XbztxHiK1i4SQ4yOsTz3Qft1
Çıktı adres:  https://karar-sende-media.vercel.app/<dosya adı>
"""
import os, sys, time, json, hashlib, shutil, argparse
import requests
from dotenv import load_dotenv
BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
TOKEN, TEAM = os.environ.get("VERCEL_TOKEN"), os.environ.get("VERCEL_TEAM_ID")
PROJECT = "karar-sende-media"; MEDIA = os.path.join(BASE, "medya")
API = "https://api.vercel.com"
H = {"Authorization": f"Bearer {TOKEN}"}

def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def deploy():
    if not TOKEN: sys.exit("VERCEL_TOKEN .env dosyasında yok.")
    files = []
    for name in sorted(os.listdir(MEDIA)):
        p = os.path.join(MEDIA, name)
        if not os.path.isfile(p): continue
        s, size = sha1(p), os.path.getsize(p)
        r = requests.post(f"{API}/v2/files", params={"teamId": TEAM}, timeout=900, data=open(p, "rb"),
                          headers={**H, "Content-Length": str(size), "x-vercel-digest": s, "Content-Type": "application/octet-stream"})
        if r.status_code not in (200, 201): sys.exit(f"Yükleme hatası {name}: {r.status_code} {r.text[:200]}")
        files.append({"file": name, "sha": s, "size": size}); print("yüklendi:", name, f"{size/1e6:.1f} MB")
    body = {"name": PROJECT, "project": PROJECT, "target": "production", "files": files, "projectSettings": {"framework": None}}
    r = requests.post(f"{API}/v13/deployments", params={"teamId": TEAM, "forceNew": 1, "skipAutoDetectionConfirmation": 1}, headers=H, json=body, timeout=120)
    if r.status_code not in (200, 201): sys.exit(f"Dağıtım hatası: {r.status_code} {r.text[:400]}")
    d = r.json(); did = d["id"]; print("dağıtım:", did)
    for _ in range(60):
        st = requests.get(f"{API}/v13/deployments/{did}", params={"teamId": TEAM}, headers=H, timeout=30).json().get("readyState")
        if st == "READY": break
        if st in ("ERROR", "CANCELED"): sys.exit(f"Dağıtım durumu: {st}")
        time.sleep(4)
    print("hazır. Adres: https://%s.vercel.app/<dosya>" % PROJECT)
    for f in files:
        u = f"https://{PROJECT}.vercel.app/{f['file']}"
        h = requests.head(u, allow_redirects=True, timeout=30, headers={"User-Agent": "facebookexternalhit/1.1"})
        ok = h.status_code == 200 and int(h.headers.get("Content-Length", 0)) == f["size"]
        print(("✔" if ok else "✘ ERİŞİLEMİYOR (Vercel Deployment Protection kapatılmalı?)"), u, h.status_code, h.headers.get("Content-Length"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--ekle"); a = ap.parse_args()
    os.makedirs(MEDIA, exist_ok=True)
    if a.ekle: shutil.copy(a.ekle, os.path.join(MEDIA, os.path.basename(a.ekle)))
    deploy()
