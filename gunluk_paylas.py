"""Her gün (Görev Zamanlayıcı) çalışır: kuyruktaki sıradaki bölümü Instagram'a Reels olarak yayınlar.

kuyruk.json alanları: url (Vercel adresi), caption, when ("YYYY-MM-DD HH:MM" yerel; null=elle), posted
Güvenlik: hesabın kullanıcı adı BEKLENEN_KULLANICI ile eşleşmezse HİÇBİR ŞEY yayınlamaz (yüzük hesabı kalıntısına paylaşım olmasın).
Günde en fazla 1 yayın. Log: log.txt
  python gunluk_paylas.py            -> gerçekten yayınlar (zamanı gelmişse)
  python gunluk_paylas.py --dry      -> container oluşturur, yayınlamaz
"""
import os, sys, json, argparse, time
from datetime import datetime, timezone
import requests
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
BASE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BASE)
import yayinla as y
BEKLENEN_KULLANICI = "kararsende_123"
QUEUE, LOG = os.path.join(BASE, "kuyruk.json"), os.path.join(BASE, "log.txt")

def log(m):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {m}"; print(line)
    open(LOG, "a", encoding="utf-8").write(line + "\n")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    q = json.load(open(QUEUE, encoding="utf-8-sig"))
    nxt = next((it for it in q if not it.get("posted")), None)
    if not nxt: return log("Kuyruk boş: paylaşılacak bölüm kalmadı.")
    if not nxt.get("url"): return log("Sıradaki bölümde 'url' yok (Vercel'e yüklenmemiş).")
    if nxt.get("when") and datetime.now() < datetime.strptime(nxt["when"], "%Y-%m-%d %H:%M"): return log(f"Zamanı gelmedi: {nxt['when']}")
    son = [datetime.fromisoformat(it["posted_at"]) for it in q if it.get("posted") and it.get("posted_at")]
    if son and not a.dry and (datetime.now(timezone.utc) - max(son)).total_seconds() < 12 * 3600:
        return log("Son paylaşımın üzerinden 12 saat geçmedi, atlandı (günde en fazla 1-2 bölüm).")
    me = requests.get(f"{y.GRAPH_URL}/{y.IG_USER_ID}", params={"fields": "username", "access_token": y.ACCESS_TOKEN}, timeout=30).json()
    if me.get("username") != BEKLENEN_KULLANICI:
        return log(f"DURDU: hesap kullanıcı adı '{me.get('username')}' (beklenen '{BEKLENEN_KULLANICI}').")
    h = requests.head(nxt["url"], allow_redirects=True, timeout=30)
    if h.status_code != 200 or int(h.headers.get("Content-Length", 0)) < 100000: return log(f"DURDU: video adresi erişilemiyor {h.status_code} {h.headers.get('Content-Length')}")
    try:
        cid = y.create_media_container(nxt["caption"], video_url=nxt["url"], media_type="REELS")
        if not y.wait_for_container_ready(cid, timeout=300): log("UYARI: zaman aşımı, yine de deneniyor")
        if a.dry: return log(f"DRY-RUN tamam, container {cid} hazır, yayınlanmadı.")
        mid = y.publish_media(cid)
        nxt.update(posted=True, media_id=mid, posted_at=datetime.now(timezone.utc).isoformat())
        json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        log(f"YAYINLANDI: {nxt['url']} media_id={mid}")
    except Exception as e:
        log(f"HATA: {str(e).replace(y.ACCESS_TOKEN, '***')[:300]}")

if __name__ == "__main__":
    main()
