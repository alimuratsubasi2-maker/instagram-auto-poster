"""Üretilmiş bölümü kuyruğa ekler:  python bolum_ekle.py 2
Gerekenler: medya/b02.mp4 (uret_bolum.py üretir), Copadam-Nisi/hikaye/ep2/caption.txt. Vercel'e yüklemeyi (vercel_yukle.py) ÖNCE çalıştır."""
import os, sys, json
BASE = os.path.dirname(os.path.abspath(__file__)); n = int(sys.argv[1])
cap = open(os.path.join(BASE, "..", "Copadam-Nisi", "hikaye", f"ep{n}", "caption.txt"), encoding="utf-8").read().strip()
url = f"https://karar-sende-media.vercel.app/b{n:02d}.mp4"
q = json.load(open(os.path.join(BASE, "kuyruk.json"), encoding="utf-8-sig"))
for it in q:
    if it.get("url") == url:
        it["caption"] = cap; print("güncellendi:", url); break
else:
    q.append({"video": f"medya/b{n:02d}.mp4", "url": url, "caption": cap, "when": None, "posted": False}); print("eklendi:", url)
json.dump(q, open(os.path.join(BASE, "kuyruk.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
