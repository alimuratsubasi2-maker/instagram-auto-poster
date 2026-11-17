"""
Instagram Yayinci - yuzuk gorsellerini Instagram Business hesabina otomatik paylasir.

Akis:
1) Yerel gorseli catbox.moe'ye yukleyip genel (public) bir URL alir
   (Instagram Graph API'nin image_url ile calismasi icin gerekli - hesap/kayit gerektirmez)
2) Instagram Graph API ile medya container'i olusturur
3) Container hazir olana kadar bekler
4) Container'i yayinlar (--publish verilmezse sadece test/dry-run yapar, GERCEKTEN PAYLASMAZ)

Kullanim:
  python yayinla.py "gorsel.png" --caption "Metin buraya #hashtag" --publish
  python yayinla.py "gorsel.png" --caption "Metin buraya"              # dry-run (test)
"""
import os
import sys
import time
import argparse
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

IG_USER_ID = os.environ.get("IG_BUSINESS_ACCOUNT_ID")
ACCESS_TOKEN = os.environ.get("IG_PAGE_ACCESS_TOKEN")
GRAPH_VERSION = "v21.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"


def upload_to_catbox(file_path: str) -> str:
    last = ""
    for attempt in range(4):
        try:
            with open(file_path, "rb") as f:
                resp = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": f},
                    timeout=300,
                )
            url = resp.text.strip()
            if resp.ok and url.startswith("http"):
                return url
            last = f"{resp.status_code} {url[:120]}"
        except Exception as e:  # gecici ag/sunucu hatasi
            last = repr(e)[:120]
        print(f"      Catbox denemesi {attempt + 1} basarisiz ({last}), tekrar deneniyor...")
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Catbox yukleme hatasi: {last}")


def create_media_container(caption: str, image_url: str = None, video_url: str = None, media_type: str = None) -> str:
    data = {"caption": caption, "access_token": ACCESS_TOKEN}
    if image_url:
        data["image_url"] = image_url
    if video_url:
        data["video_url"] = video_url
    if media_type:
        data["media_type"] = media_type
    resp = requests.post(
        f"{GRAPH_URL}/{IG_USER_ID}/media",
        data=data,
        timeout=30,
    )
    data = resp.json()
    if "id" not in data:
        raise RuntimeError(f"Container olusturma hatasi: {data}")
    return data["id"]


def wait_for_container_ready(creation_id: str, timeout: int = 60) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"{GRAPH_URL}/{creation_id}",
            params={"fields": "status_code", "access_token": ACCESS_TOKEN},
            timeout=30,
        )
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError("Container isleme hatasi (ERROR)")
        time.sleep(3)
    return False


def publish_media(creation_id: str) -> str:
    resp = requests.post(
        f"{GRAPH_URL}/{IG_USER_ID}/media_publish",
        data={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
        timeout=30,
    )
    data = resp.json()
    if "id" not in data:
        raise RuntimeError(f"Yayinlama hatasi: {data}")
    return data["id"]


def post_image(image_path: str, caption: str, dry_run: bool = True):
    if not IG_USER_ID or not ACCESS_TOKEN:
        raise RuntimeError(".env dosyasinda IG_BUSINESS_ACCOUNT_ID / IG_PAGE_ACCESS_TOKEN eksik")

    print(f"[1/4] Gorsel yukleniyor: {image_path}")
    image_url = upload_to_catbox(image_path)
    print(f"      Genel URL: {image_url}")

    print("[2/4] Instagram medya container'i olusturuluyor...")
    creation_id = create_media_container(caption, image_url=image_url)
    print(f"      creation_id: {creation_id}")

    print("[3/4] Islenmesi bekleniyor...")
    ready = wait_for_container_ready(creation_id)
    if not ready:
        print("      UYARI: zaman asimi, yine de yayinlamayi deniyorum")

    if dry_run:
        print("[4/4] DRY-RUN modu - GERCEK PAYLASIM YAPILMADI.")
        print("      Gercekten paylasmak icin --publish parametresini ekleyin.")
        return None

    print("[4/4] Yayinlaniyor...")
    media_id = publish_media(creation_id)
    print(f"      BASARILI! Yayinlanan medya ID: {media_id}")
    return media_id


def post_video(video_path: str, caption: str, dry_run: bool = True):
    """Bir videoyu Reels olarak Instagram'a paylasir."""
    if not IG_USER_ID or not ACCESS_TOKEN:
        raise RuntimeError(".env dosyasinda IG_BUSINESS_ACCOUNT_ID / IG_PAGE_ACCESS_TOKEN eksik")

    print(f"[1/4] Video yukleniyor: {video_path}")
    video_url = upload_to_catbox(video_path)
    print(f"      Genel URL: {video_url}")

    print("[2/4] Instagram Reels container'i olusturuluyor...")
    creation_id = create_media_container(caption, video_url=video_url, media_type="REELS")
    print(f"      creation_id: {creation_id}")

    print("[3/4] Video islenmesi bekleniyor (bu fotograftan daha uzun surebilir)...")
    ready = wait_for_container_ready(creation_id, timeout=180)
    if not ready:
        print("      UYARI: zaman asimi, yine de yayinlamayi deniyorum")

    if dry_run:
        print("[4/4] DRY-RUN modu - GERCEK PAYLASIM YAPILMADI.")
        print("      Gercekten paylasmak icin --publish parametresini ekleyin.")
        return None

    print("[4/4] Yayinlaniyor...")
    media_id = publish_media(creation_id)
    print(f"      BASARILI! Yayinlanan Reels ID: {media_id}")
    return media_id


def post_video_resumable(video_path: str, caption: str, dry_run: bool = True, attempts: int = 8):
    """Instagram'in dogrudan yukleme sunucusu araliklarla 'ProcessingFailedError' verebiliyor (2026-11-14 testleri:
    ayni dosya bazen gecti, bazen gecmedi). Bu yuzden her denemede yeni container acilarak tekrar denenir."""
    last = None
    for n in range(1, attempts + 1):
        try:
            return _post_video_resumable_once(video_path, caption, dry_run)
        except RuntimeError as e:
            last = e
            if "Dogrudan yukleme basarisiz" not in str(e) and "ERROR" not in str(e):
                raise
            print(f"      Deneme {n}/{attempts} basarisiz, yeni container ile tekrar deneniyor...")
            time.sleep(6)
    raise last


def _post_video_resumable_once(video_path: str, caption: str, dry_run: bool = True):
    """Videoyu ucuncu taraf barindirma olmadan, Instagram'a dogrudan yukleyerek Reels yapar (resumable upload)."""
    if not IG_USER_ID or not ACCESS_TOKEN:
        raise RuntimeError(".env dosyasinda IG_BUSINESS_ACCOUNT_ID / IG_PAGE_ACCESS_TOKEN eksik")
    size = os.path.getsize(video_path)
    print(f"[1/4] Reels container'i (resumable) olusturuluyor... ({size/1e6:.1f} MB)")
    r = requests.post(f"{GRAPH_URL}/{IG_USER_ID}/media",
                      data={"media_type": "REELS", "upload_type": "resumable", "caption": caption, "access_token": ACCESS_TOKEN},
                      timeout=60).json()
    if "id" not in r:
        raise RuntimeError(f"Container olusturma hatasi: {r}")
    cid = r["id"]
    uri = r.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_VERSION}/{cid}"
    print(f"      creation_id: {cid}")
    print("[2/4] Video dogrudan Instagram'a yukleniyor...")
    chunk = int(os.environ.get("IG_CHUNK_MB", "0")) * 1024 * 1024 or size
    with open(video_path, "rb") as f:
        offset = 0
        while offset < size:
            part = f.read(chunk)
            up = requests.post(uri, headers={"Authorization": f"OAuth {ACCESS_TOKEN}", "offset": str(offset), "file_size": str(size),
                                             "Content-Type": "application/octet-stream"},
                               data=part, timeout=900)
            print(f"      parca offset={offset} ({len(part)/1e6:.1f} MB): {up.status_code} {up.text[:120]}")
            if not up.ok:
                raise RuntimeError(f"Dogrudan yukleme basarisiz: {up.status_code} {up.text[:300]}")
            offset += len(part)
    print("[3/4] Video islenmesi bekleniyor...")
    if not wait_for_container_ready(cid, timeout=300):
        print("      UYARI: zaman asimi, yine de yayinlamayi deniyorum")
    if dry_run:
        print("[4/4] DRY-RUN modu - GERCEK PAYLASIM YAPILMADI.")
        return None
    print("[4/4] Yayinlaniyor...")
    media_id = publish_media(cid)
    print(f"      BASARILI! Yayinlanan Reels ID: {media_id}")
    return media_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram'a gorsel/video yayinlar")
    parser.add_argument("image", help="Yerel gorsel/video dosya yolu")
    parser.add_argument("--caption", default="", help="Paylasim metni (caption)")
    parser.add_argument("--video", action="store_true", help="Dosyayi Reels (video) olarak paylas")
    parser.add_argument("--publish", action="store_true", help="Gercekten yayinla (yoksa sadece test/dry-run)")
    args = parser.parse_args()
    if args.video:
        post_video(args.image, args.caption, dry_run=not args.publish)
    else:
        post_image(args.image, args.caption, dry_run=not args.publish)
