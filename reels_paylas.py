"""KARAR SENDE — kuyruktaki sıradaki bölümü Reels olarak yayınlar.

  python reels_paylas.py              -> TEST (dry-run): yükler, container oluşturur, YAYINLAMAZ
  python reels_paylas.py --publish    -> zamanı gelmiş sıradaki bölümü gerçekten yayınlar
  python reels_paylas.py --publish --force   -> zamanına bakmadan sıradakini yayınlar
  python reels_paylas.py --status     -> kuyruğu listeler

kuyruk.json alanları: video (yol), caption, when (yerel saat "YYYY-MM-DD HH:MM" ya da null=elle), posted, media_id, posted_at
"""
import os, sys, json, argparse
from datetime import datetime, timezone
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
QUEUE = os.path.join(BASE, "kuyruk.json")

def load():
    return json.load(open(QUEUE, encoding="utf-8-sig"))

def save(q):
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def due(item, force):
    if item.get("posted"): return False
    if force or not item.get("when"): return force or False
    return datetime.now() >= datetime.strptime(item["when"], "%Y-%m-%d %H:%M")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true"); ap.add_argument("--force", action="store_true"); ap.add_argument("--status", action="store_true")
    a = ap.parse_args(); q = load()
    if a.status:
        for i, it in enumerate(q):
            print(f"{i+1:>2}. {'✔' if it.get('posted') else '·'} {it.get('when') or 'elle'}  {os.path.basename(it['video'])}")
        return
    # sıradaki paylaşılmamış bölüm (sıra bozulmasın: sadece ilk paylaşılmamış bölüme bakılır)
    nxt = next((it for it in q if not it.get("posted")), None)
    if nxt is None:
        print("Kuyrukta paylaşılacak bölüm kalmadı."); return
    if a.publish and not due(nxt, a.force):
        print(f"Sıradaki bölümün zamanı gelmedi (when={nxt.get('when')}). --force ile zorlayabilirsin."); return
    from yayinla import post_video_resumable
    print("Sıradaki:", os.path.basename(nxt["video"]))
    media_id = post_video_resumable(nxt["video"], nxt["caption"], dry_run=not a.publish)
    if a.publish and media_id:
        nxt["posted"] = True; nxt["media_id"] = media_id; nxt["posted_at"] = datetime.now(timezone.utc).isoformat(); save(q)
        print("Kuyruk güncellendi.")

if __name__ == "__main__":
    main()
