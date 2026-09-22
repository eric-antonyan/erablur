from pathlib import Path

from app.db.database import Database
from app.utils.armenian_search import normalize_armenian_text


def _seed(database: Database) -> None:
    database.save_hero("robert-abajyan", {
        "first_name": "Ռոբերտ",
        "last_name": "Աբաջյան",
        "region": "Երևան",
        "war": "Քառօրյա պատերազմ",
        "bio": "Ռոբերտ Աբաջյանի թանգարանային գրառում։",
    })
    database.save_hero("robert-hovhannisyan", {
        "first_name": "Ռոբերտ",
        "last_name": "Հովհաննիսյան",
        "region": "Լոռի",
        "war": "44-օրյա պատերազմ",
        "bio": "Այլ Ռոբերտի գրառում։",
    })
    database.save_hero("sevak-serobyan", {
        "first_name": "Սեվակ",
        "last_name": "Սերոբյան",
        "region": "Լոռի",
        "war": "44-օրյա պատերազմ",
        "bio": "Սեվակ Սերոբյանի թանգարանային գրառում։",
    })
    database.save_hero("sevak-aleksanyan", {
        "first_name": "Սեվակ",
        "last_name": "Ալեքսանյան",
        "region": "Արագածոտն",
        "war": "44-օրյա պատերազմ",
        "bio": "Այլ Սեվակի գրառում։",
    })


def test_inflected_full_name_beats_same_first_name(tmp_path: Path) -> None:
    database = Database(str(tmp_path / "heroes.db"))
    _seed(database)

    records = database.search_heroes_for_context("Պատմիր Ռոբերտ Աբաջյանի մասին", 6)

    assert [record["id"] for record in records] == ["robert-abajyan"]


def test_armenian_yev_spelling_and_declension(tmp_path: Path) -> None:
    database = Database(str(tmp_path / "heroes.db"))
    _seed(database)

    records = database.search_heroes_for_context(
        "որտեղի՞ց էր հերոս Սևակ Սերոբյանը, և ո՞ր պատերազմի մասնակից է",
        6,
    )

    assert [record["id"] for record in records] == ["sevak-serobyan"]
    assert records[0]["region"] == "Լոռի"
    assert records[0]["war"] == "44-օրյա պատերազմ"


def test_small_surname_typo_still_resolves_unique_person(tmp_path: Path) -> None:
    database = Database(str(tmp_path / "heroes.db"))
    _seed(database)

    records = database.search_heroes_for_context("Պատմիր Ռոբերտ Աբաջյնաի մասին", 6)

    assert [record["id"] for record in records] == ["robert-abajyan"]


def test_armenian_question_marks_do_not_split_words() -> None:
    assert normalize_armenian_text("որտեղի՞ց և ո՞ր") == "որտեղից և որ"
