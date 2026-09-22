import requests
from bs4 import BeautifulSoup
import json
import logging
import re
from time import sleep
import os
<<<<<<< HEAD
=======
from app.db.database import db
import uuid
>>>>>>> 54c1deb (commit)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_URL = "https://www.zinapah.am/hy/fallen-heroes"
OUTPUT_FILE = "data/heroes.json"

<<<<<<< HEAD
# Ensure file exists as an empty list
if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)
=======
                          
os.makedirs("data", exist_ok=True)
>>>>>>> 54c1deb (commit)

def fetch_bio(bio_link):
    """Fetch hero bio as Telegram-style HTML."""
    try:
        response = requests.get(bio_link)
        if response.status_code != 200:
            logging.warning(f"Failed to fetch bio page: {bio_link}")
            return ""
        soup = BeautifulSoup(response.text, "html.parser")
        bio_div = soup.select_one(".soldiers-inner__right .d-flex.flex-column.gap-8")
        if not bio_div:
            return ""
<<<<<<< HEAD
        # Keep HTML intact for Telegram
=======
>>>>>>> 54c1deb (commit)
        bio_html = "".join(str(p) for p in bio_div.find_all("p"))
        return bio_html
    except Exception as e:
        logging.error(f"Error fetching bio: {e}")
        return ""

<<<<<<< HEAD

=======
>>>>>>> 54c1deb (commit)
def parse_dates(date_str, bio_text=""):
    birth = ""
    dead = ""
    match = re.match(r"(\d{4})\s*-\s*(\d{4})", date_str)
    if match:
        birth = f"{match.group(1)} թ․"
        dead = f"{match.group(2)} թ․"
    else:
        dead = date_str.strip()
        bio_match = re.search(r"Ծնվել է\s*([\d\s\.\-թ․]+)", bio_text)
        if bio_match:
            birth = bio_match.group(1).strip()
    return {"birth": birth, "dead": dead}

<<<<<<< HEAD
def save_hero(hero):
    """Append hero to JSON file."""
    try:
        with open(OUTPUT_FILE, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data.append(hero)
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving hero: {e}")

=======
>>>>>>> 54c1deb (commit)
def fetch_heroes():
    page = 1
    i = 1
    while True:
        url = f"{BASE_URL}?page={page}"
        logging.info(f"Fetching page {page}: {url}")
        response = requests.get(url)
        if response.status_code != 200:
            logging.warning(f"Failed to fetch page {page}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        soldier_items = soup.find_all("div", class_="soldier-item")

        if not soldier_items:
            logging.info(f"No hero items found on page {page}. Stopping.")
            break

        for item in soldier_items:
            full_name = item.select_one(".soldier-item__name").get_text(strip=True)
            name_parts = full_name.split()
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            date_str = item.select_one(".soldier-item__date").get_text(strip=True)
            region = item.select_one(".soldier-item__region").get_text(strip=True) if item.select_one(".soldier-item__region") else ""
            war = item.select_one(".soldier-item__war").get_text(strip=True) if item.select_one(".soldier-item__war") else ""
            img_url = item.select_one(".soldier-item__img")['src'].strip() if item.select_one(".soldier-item__img") else ""
            bio_link = item.select_one(".soldier-item__bio-link")['href'] if item.select_one(".soldier-item__bio-link") else ""

            bio_text = fetch_bio(bio_link) if bio_link else ""
            dates = parse_dates(date_str, bio_text)

            hero = {
                "name": {"first": first_name, "last": last_name},
                "date": dates,
                "region": region,
                "war": war,
                "img_url": img_url,
                "bio_link": bio_link,
                "bio": bio_text
            }

<<<<<<< HEAD
            save_hero(hero)
            logging.info(f"{i} Saved hero: {full_name}")
            i = i + 1

            sleep(0.5)  # polite delay
=======
                                         
            hero_id = str(uuid.uuid4())
            db.save_hero(hero_id, hero)
            
            logging.info(f"{i} Saved hero: {full_name}")
            i += 1
            sleep(0.5)
>>>>>>> 54c1deb (commit)

        page += 1

if __name__ == "__main__":
    logging.info("Starting scraping heroes...")
<<<<<<< HEAD
    fetch_heroes()
=======
    fetch_heroes()
>>>>>>> 54c1deb (commit)
