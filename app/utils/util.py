<<<<<<< HEAD
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
=======
from __future__ import annotations

import asyncio
import datetime
import ipaddress
import socket
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError
from loguru import logger


def format_armenian_datetime(dt_value):
    """Format a date/time value in Armenian without failing on missing values."""
    if not dt_value or dt_value == "Չկա":
        return "Չկա"
    try:
        if isinstance(dt_value, str):
            dt = datetime.datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
        else:
            dt = dt_value
    except Exception:
        return str(dt_value)

    months_hy = [
        "հունվար", "փետրվար", "մարտ", "ապրիլ", "մայիս", "հունիս",
        "հուլիս", "օգոստոս", "սեպտեմբեր", "հոկտեմբեր", "նոյեմբեր", "դեկտեմբեր",
>>>>>>> 54c1deb (commit)
    ]
    return f"{dt.day} {months_hy[dt.month - 1]} {dt.year} թ․, {dt.hour:02d}:{dt.minute:02d}"


<<<<<<< HEAD
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
=======
TEMP_PATH = Path("temp")
LOGO_PATH = Path("data/logo.png")
MAX_IMAGE_BYTES = 15 * 1024 * 1024
_session = requests.Session()
_session.headers.update({"User-Agent": "ArmenianHeroesMuseumBot/2.0"})


def _public_http_url(url: str) -> bool:
    """Basic SSRF protection for admin/database supplied image URLs."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        host = parsed.hostname.lower()
        if host in {"localhost", "localhost.localdomain"}:
            return False
        # Reject literal private/loopback/link-local IPs. DNS hostnames are
        # resolved and checked where possible.
        try:
            addresses = {ipaddress.ip_address(parsed.hostname)}
        except ValueError:
            addresses = {
                ipaddress.ip_address(info[4][0])
                for info in socket.getaddrinfo(parsed.hostname, None)
            }
        return all(not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved) for ip in addresses)
    except Exception:
        return False


def _download_image(url: str) -> Image.Image | None:
    if not url or not _public_http_url(url):
        return None
    try:
        with _session.get(url, timeout=(5, 15), stream=True, allow_redirects=True) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if content_type and not content_type.startswith("image/"):
                return None
            data = bytearray()
            for chunk in response.iter_content(64 * 1024):
                data.extend(chunk)
                if len(data) > MAX_IMAGE_BYTES:
                    raise ValueError("image exceeds safety limit")
        image = Image.open(BytesIO(data))
        image.load()
        return image
    except (requests.RequestException, UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning("Image download failed for {}: {}", url, exc)
        return None


def _flag_background(size: int = 900) -> Image.Image:
    image = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(image)
    band = size // 3
    draw.rectangle((0, 0, size, band), fill=(217, 0, 18))
    draw.rectangle((0, band, size, band * 2), fill=(0, 51, 160))
    draw.rectangle((0, band * 2, size, size), fill=(242, 168, 0))
    return image


def _compose_hero_image_sync(hero_img_url: str) -> str:
    TEMP_PATH.mkdir(parents=True, exist_ok=True)
    output = TEMP_PATH / f"hero_{uuid4().hex[:10]}.png"

    canvas = _flag_background(900).convert("RGBA")
    canvas = ImageEnhance.Brightness(canvas).enhance(0.78)
    hero = _download_image(hero_img_url)

    if hero is not None:
        hero = ImageOps.exif_transpose(hero).convert("RGBA")
        fitted = ImageOps.contain(hero, (720, 780), Image.Resampling.LANCZOS)
        # Soft rounded-rectangle portrait panel.
        panel_size = (fitted.width + 40, fitted.height + 40)
        panel = Image.new("RGBA", panel_size, (255, 255, 255, 230))
        mask = Image.new("L", panel_size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel_size[0] - 1, panel_size[1] - 1), radius=36, fill=255)
        panel.putalpha(mask)
        panel.alpha_composite(fitted, ((panel.width - fitted.width) // 2, (panel.height - fitted.height) // 2))

        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_panel = Image.new("RGBA", panel.size, (0, 0, 0, 170))
        shadow_panel.putalpha(mask.filter(ImageFilter.GaussianBlur(14)))
        x = (canvas.width - panel.width) // 2
        y = (canvas.height - panel.height) // 2
        shadow.alpha_composite(shadow_panel, (x + 10, y + 14))
        canvas = Image.alpha_composite(canvas, shadow)
        canvas.alpha_composite(panel, (x, y))

    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((150, 150), Image.Resampling.LANCZOS)
            canvas.alpha_composite(logo, (canvas.width - logo.width - 24, canvas.height - logo.height - 24))
        except OSError:
            pass

    canvas.convert("RGB").save(output, "PNG", optimize=True)
    return str(output)


async def compose_hero_image(hero_img_url: str) -> str:
    """Create the Telegram hero card without blocking the event loop."""
    return await asyncio.to_thread(_compose_hero_image_sync, hero_img_url or "")


def remove_temp_file(path: str | None) -> None:
    if not path:
        return
    try:
        candidate = Path(path)
        if candidate.is_file() and candidate.resolve().parent == TEMP_PATH.resolve():
            candidate.unlink(missing_ok=True)
    except OSError:
        pass
>>>>>>> 54c1deb (commit)
