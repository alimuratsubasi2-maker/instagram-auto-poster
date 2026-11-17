# Instagram Otomatik YayÄ±ncÄ±

GÃ¶rselleri ve reels videolarÄ±nÄ± **Instagram Business** hesabÄ±na otomatik paylaÅŸan betikler. ZamanlanmÄ±ÅŸ kuyruk ile gÃ¼nlÃ¼k paylaÅŸÄ±m yapar.

## AkÄ±ÅŸ
1. Yerel gÃ¶rsel geÃ§ici olarak genel bir URL'ye yÃ¼klenir (Graph API `image_url` ister)
2. Instagram Graph API ile medya container'Ä± oluÅŸturulur
3. HazÄ±r olana kadar beklenir, ardÄ±ndan yayÄ±nlanÄ±r

## Dosyalar
`yayinla.py` (gÃ¶rsel) Â· `reels_paylas.py` (video) Â· `gunluk_paylas.py` (gÃ¼nlÃ¼k zamanlama) Â· `vercel_yukle.py` (medya barÄ±ndÄ±rma)

```bash
pip install requests
cp .env.example .env     # IG_USER_ID, IG_ACCESS_TOKEN
python yayinla.py
```

**Teknolojiler:** Python Â· Instagram Graph API Â· Vercel