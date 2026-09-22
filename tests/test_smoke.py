from pathlib import Path

from app.db.database import Database
from app.handlers.museum_search import build_caption, build_keyboard


def test_database_round_trip(tmp_path: Path):
    database = Database(str(tmp_path / "heroes.db"))
    database.save_hero("hero-1", {
        "first_name": "Արամ",
        "last_name": "Օրինակյան",
        "region": "Երևան",
        "war": "Փորձնական գրառում",
        "bio": "Կենսագրական տվյալ։",
    })
    hero = database.get_hero("hero-1")
    assert hero is not None
    assert hero["first_name"] == "Արամ"
    assert database.get_heroes_by_name("Արամ")[0]["id"] == "hero-1"
    assert database.search_heroes_for_context("Պատմիր Արամ Օրինակյանի մասին")[0]["id"] == "hero-1"


def test_caption_and_keyboard_limits():
    hero = {
        "id": "hero-1",
        "first_name": "Արամ",
        "last_name": "Օրինակյան",
        "birth_date": "2000",
        "death_date": "2020",
        "region": "Երևան",
        "war": "Գործողություն",
        "bio": "Շատ երկար տեքստ " * 300,
        "bio_link": "https://example.com",
    }
    caption = build_caption(hero, 0, 1)
    assert len(caption) <= 1024
    keyboard = build_keyboard("all", 0, 1, "key", hero["id"], hero["bio_link"])
    assert keyboard.inline_keyboard


def test_donation_round_trip(tmp_path: Path):
    database = Database(str(tmp_path / "payments.db"))
    database.create_donation(
        "star_test",
        user_id=42,
        provider="telegram_stars",
        amount="100",
        currency="XTR",
    )
    pending = database.get_donation("star_test")
    assert pending is not None
    assert pending["status"] == "pending"
    database.update_donation(
        "star_test",
        status="completed",
        telegram_charge_id="charge-id",
        paid_amount="100",
        paid_currency="XTR",
        mark_paid=True,
    )
    stats = database.get_donation_stats()
    assert stats["paid_orders"] == 1
    assert stats["stars_total"] == 100
