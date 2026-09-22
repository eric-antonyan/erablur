import datetime
import os
import requests
from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError

# Armenian date formatting
def format_armenian_datetime(dt_str: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return dt_str

    months_hy = [
        "հունվար", "փետրվար", "մարտ", "ապրիլ", "մայիս", "հունիս",
        "հուլիս", "օգոստոս", "սեպտեմբեր", "հոկտեմբեր", "նոյեմբեր", "դեկտեմբեր"
    ]
    return f"{dt.day} {months_hy[dt.month - 1]} {dt.year} թ․, {dt.hour:02d}:{dt.minute:02d}"


# Image URLs
ARMENIAN_FLAG_URL = "https://flagcdn.com/w640/am.png"
LOGO_PATH = "data/logo.png"
TEMP_PATH = "temp/"
session = requests.Session()


def safe_download_image(url: str):
    """Efficient downloader with persistent session."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        with session.get(url, headers=headers, timeout=10) as r:
            r.raise_for_status()
            img = Image.open(BytesIO(r.content))
            img.load()
            return img
    except (requests.RequestException, UnidentifiedImageError) as e:
        print(f"⚠️ Failed to load image: {url} ({e})")
        return None


# Compose optimized
async def compose_hero_image(hero_img_url: str) -> str:
    os.makedirs(TEMP_PATH, exist_ok=True)
    out_path = os.path.join(TEMP_PATH, f"hero_{uuid4().hex[:6]}.png")

    try:
        # Load background
        flag = safe_download_image(ARMENIAN_FLAG_URL)
        if not flag:
            raise RuntimeError("Flag image could not be loaded")
        flag = flag.convert("RGB").resize((800, 800), Image.LANCZOS)
        flag = ImageEnhance.Brightness(flag).enhance(0.85)

        # Load hero
        hero = safe_download_image(hero_img_url)
        if not hero:
            flag.save(out_path, "PNG")
            return out_path
        hero = hero.convert("RGBA")

        # Crop transparent edges if any
        bbox = hero.getbbox()
        if bbox:
            hero = hero.crop(bbox)

        # Resize hero to full 100%
        hero = hero.resize(flag.size, Image.LANCZOS)

        # Add soft shadow for depth
        shadow = hero.copy().convert("RGBA").filter(ImageFilter.GaussianBlur(8))
        shadow_layer = Image.new("RGBA", flag.size, (0, 0, 0, 0))
        shadow_layer.paste(shadow, (10, 10), shadow)
        flag = Image.alpha_composite(flag.convert("RGBA"), shadow_layer)

        # Overlay hero (full)
        flag.paste(hero, (0, 0), hero)

        # Add logo top-right (z-index 999)
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            size = int(flag.width * 0.18)
            logo = logo.resize((size, int(size * logo.height / logo.width)), Image.LANCZOS)
            flag.paste(logo, (flag.width - logo.width - 20, flag.height - logo.height - 20), logo)

        flag.save(out_path, "PNG", optimize=True)
        print(f"✅ Optimized hero image saved: {out_path}")
        return out_path

    except Exception as e:
        print(f"⚠️ Fast compose failed: {e}")
        return hero_img_url
