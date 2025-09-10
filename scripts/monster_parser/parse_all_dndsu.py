#!/usr/bin/env python3
import argparse
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient

# Optional imports for crawling
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import hashlib
import time
import re


def build_mongo_client(uri: str) -> MongoClient:
    return MongoClient(uri)


def upsert_dummy(db_name: str, coll_name: str, uri: str) -> Dict[str, Any]:
    client = build_mongo_client(uri)
    db = client[db_name]
    coll = db[coll_name]

    now_iso = datetime.utcnow().isoformat() + "Z"
    doc = {
        "source": {
            "provider": "dnd.su",
            "url": "about:dummy",
            "slug": "dummy",
            "page_codes": []
        },
        "ingest": {
            "schema_version": 1,
            "parser_version": "v0.0.1",
            "fetched_at": now_iso,
            "content_hash": "dummy"
        },
        "raw": {"html": "", "text": ""},
        "extracted": {"title": {"ru": "Тест", "en": "Test"}},
        "labels": ["dndsu_v1"],
        "diagnostics": {"warnings": [], "errors": []}
    }

    # upsert by unique url
    result = coll.update_one({"source.url": doc["source"]["url"]}, {"$set": doc}, upsert=True)
    client.close()
    return {
        "matched": result.matched_count,
        "modified": result.modified_count,
        "upserted_id": str(result.upserted_id) if result.upserted_id else None,
    }


def _is_valid_bestiary_item(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.netloc.lower() != "dnd.su":
            return False
        path = parsed.path or ""
        if not path.startswith("/bestiary/"):
            return False
        if path.rstrip("/") == "/bestiary":
            return False
        if path.startswith("/articles/"):
            return False
        return True
    except Exception:
        return False


def crawl_bestiary_links(list_url: str, base_url: str, test_limit: int, delay: float) -> List[Dict[str, str]]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36"
    })

    results: List[Dict[str, str]] = []
    visited_pages = set()
    page_url = list_url

    while page_url and page_url not in visited_pages:
        visited_pages.add(page_url)
        resp = session.get(page_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        page_links: List[Dict[str, str]] = []
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            if not href:
                continue
            full_url = urljoin(base_url, href)
            if not _is_valid_bestiary_item(full_url):
                continue
            if not any(m["url"] == full_url for m in results):
                page_links.append({"name": a.get_text(strip=True), "url": full_url})

        results.extend(page_links)
        print(f"Found on page: {len(page_links)}, total: {len(results)}")
        if test_limit and test_limit > 0 and len(results) >= test_limit:
            results = results[:test_limit]
            break

        next_link = None
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if text in (">", "›", "»"):
                next_link = urljoin(base_url, a["href"]) if a.get("href") else None
                break
        page_url = next_link

        if delay and delay > 0:
            time.sleep(delay)

    return results


def write_links_cache(cache_path: str, links: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"links": links, "total": len(links)}, f, ensure_ascii=False, indent=2)


def read_links_cache(cache_path: str) -> List[Dict[str, str]]:
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("links", [])
    except FileNotFoundError:
        return []


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1]


# ---------------- Core extraction helpers -----------------
# broaden size matching to include masculine/feminine/neuter and inflections
SIZE_WORDS = r"Крошечн[а-я]*|Маленьк[а-я]*|Средн[а-я]*|Больш[а-я]*|Огромн[а-я]*|Гигантск[а-я]*"


def extract_title_ru_en(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    # Try h2 like: "Русское [English] ..."
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        m = re.match(r"^([^\[]+)\s*\[([^\]]+)\]", text)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    # fallback: page <title>
    title_tag = soup.find("title")
    if title_tag:
        t = title_tag.get_text(strip=True)
        # often "Name / ..." -> take left part
        if " / " in t:
            t = t.split(" / ")[0].strip()
        return t, None
    return None, None


def extract_taxonomy(page_text: str) -> Dict[str, Optional[str]]:
    patterns = [
        rf"({SIZE_WORDS})\s+([^,\n]+),\s*([^,\n]+)",
        rf"({SIZE_WORDS})\s*\?\s+([^,\n]+),\s*([^,\n]+)",
    ]
    for p in patterns:
        m = re.search(p, page_text)
        if m:
            return {"size": m.group(1), "type": m.group(2).strip(), "alignment": m.group(3).strip()}
    return {"size": None, "type": None, "alignment": None}


def extract_ac(page_text: str) -> Dict[str, Optional[Any]]:
    m = re.search(r"Класс\s+Доспеха\s+(\d+)(?:\s*\(([^)]+)\))?", page_text)
    if m:
        return {"value": int(m.group(1)), "note": m.group(2) or None}
    return {"value": None, "note": None}


def extract_hp(page_text: str) -> Dict[str, Optional[Any]]:
    m = re.search(r"Хиты\s+(\d+)(?:\s*\(([^)]+)\))?", page_text)
    if m:
        avg = int(m.group(1))
        return {"average": avg, "formula": m.group(2) or None}
    return {"average": None, "formula": None}


def parse_speeds(speed_str: str) -> Dict[str, Optional[Any]]:
    if not speed_str:
        return {"walk": None, "fly": None, "swim": None, "climb": None, "burrow": None, "hover": None, "raw": ""}
    s = speed_str.lower().replace("ё", "е")
    s_no_paren = re.sub(r"\([^)]*\)", "", s)

    def find_first(pattern: str) -> Optional[int]:
        m = re.search(pattern, s_no_paren)
        return int(m.group(1)) if m else None

    fly = find_first(r"\b(?:летая|полета|полет|fly)\s*(\d+)\s*(?:фт|футов|фут|ft)\b")
    swim = find_first(r"\b(?:плава[а-я]*|swim)\s*(\d+)\s*(?:фт|футов|фут|ft)\b")
    climb = find_first(r"\b(?:лаза[а-я]*|climb)\s*(\d+)\s*(?:фт|футов|фут|ft)\b")
    burrow = find_first(r"\b(?:рыть[а-я]*|burrow)\s*(\d+)\s*(?:фт|футов|фут|ft)\b")

    walk = None
    segs = [seg.strip() for seg in re.split(r"[,;]", s_no_paren) if seg.strip()]
    for seg in segs:
        if not re.search(r"\b(?:fly|climb|swim|burrow|летая|полет|полета|плава|лаза|рыть)\b", seg):
            m = re.match(r"^(\d+)\s*(?:фт|футов|фут|ft)\b", seg)
            if m:
                walk = int(m.group(1))
                break
    hover = True if "парит" in s or "hover" in s else None

    return {"walk": walk, "fly": fly, "swim": swim, "climb": climb, "burrow": burrow, "hover": hover, "raw": speed_str}


def extract_speed(page_text: str) -> Dict[str, Optional[Any]]:
    m = re.search(r"Скорость\s+([^\n]+)", page_text)
    if m:
        return parse_speeds(m.group(1).strip())
    return {"walk": None, "fly": None, "swim": None, "climb": None, "burrow": None, "hover": None, "raw": ""}


def extract_abilities(page_text: str) -> Dict[str, Optional[int]]:
    patterns = [
        r"Сил\s+Лов\s+Тел\s+Инт\s+Мдр\s+Хар\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)",
        r"(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)\s+(\d+)\s*\([^)]+\)",
    ]
    for p in patterns:
        m = re.search(p, page_text)
        if m:
            return {
                "str": int(m.group(1)),
                "dex": int(m.group(2)),
                "con": int(m.group(3)),
                "int": int(m.group(4)),
                "wis": int(m.group(5)),
                "cha": int(m.group(6)),
            }
    return {"str": None, "dex": None, "con": None, "int": None, "wis": None, "cha": None}


def extract_cr(page_text: str) -> Dict[str, Optional[Any]]:
    m = re.search(r"Опасность\s+([^\s(]+)(?:\s*\(([^)]+)\s+опыта\))?", page_text)
    if m:
        value = m.group(1)
        xp = None
        if m.group(2):
            try:
                xp = int(re.sub(r"\D", "", m.group(2)))
            except Exception:
                xp = None
        return {"value": value, "xp": xp}
    return {"value": None, "xp": None}


def extract_proficiency(page_text: str) -> Optional[int]:
    m = re.search(r"Бонус\s+мастерства\s*([+-]?\d+)", page_text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

RU_ABIL_MAP = {
    "сил": "str",
    "лов": "dex",
    "тел": "con",
    "инт": "int",
    "мдр": "wis",
    "хар": "cha",
}


def extract_saving_throws(page_text: str) -> List[Dict[str, Any]]:
    m = re.search(r"Спасброски\s+([^\n]+)", page_text)
    if not m:
        return []
    payload: List[Dict[str, Any]] = []
    line = m.group(1)
    for seg in [s.strip() for s in line.split(',') if s.strip()]:
        ms = re.match(r"([А-Яа-я]{3})\s*([+-]?\d+)", seg)
        if not ms:
            continue
        abbr = ms.group(1).lower()
        ability = RU_ABIL_MAP.get(abbr)
        try:
            bonus = int(ms.group(2))
        except Exception:
            continue
        if ability:
            payload.append({"ability": ability, "bonus": bonus})
    return payload


def extract_skills(page_text: str) -> List[Dict[str, Any]]:
    m = re.search(r"Навыки\s+([^\n]+)", page_text)
    if not m:
        return []
    payload: List[Dict[str, Any]] = []
    line = m.group(1)
    for seg in [s.strip() for s in line.split(',') if s.strip()]:
        ms = re.match(r"(.+?)\s*([+-]?\d+)$", seg)
        if not ms:
            continue
        name = ms.group(1).strip()
        try:
            bonus = int(ms.group(2))
        except Exception:
            continue
        payload.append({"name": name, "bonus": bonus})
    return payload


def _find_ft(s: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:фт|футов|фут|ft)\b", s)
    return int(m.group(1)) if m else None


def extract_senses(page_text: str) -> Dict[str, Any]:
    m = re.search(r"Чувства\s+([^\n]+)", page_text, flags=re.IGNORECASE)
    raw = m.group(1).strip() if m else ""
    s = raw.lower().replace('ё', 'е')
    out = {
        "blindsight_ft": None,
        "darkvision_ft": None,
        "tremorsense_ft": None,
        "truesight_ft": None,
        "passive_perception": None,
        "raw": raw,
    }
    for key, marker in (
        ("blindsight_ft", "слепое зрение"),
        ("darkvision_ft", "темное зрение"),
        ("truesight_ft", "истинное зрение"),
        ("tremorsense_ft", "тремор"),
    ):
        if marker in s:
            out[key] = _find_ft(s)
    pm = re.search(r"пассивн[а-я\s]*воспр[а-я]*\s*(\d+)", s)
    if pm:
        try:
            out["passive_perception"] = int(pm.group(1))
        except Exception:
            pass
    return out


def extract_languages(page_text: str) -> Dict[str, Any]:
    m = re.search(r"Языки\s+([^\n]+)", page_text)
    raw = m.group(1).strip() if m else ""
    s = raw.lower()
    tele = None
    tm = re.search(r"телепат[а-я\s]*?(\d+)\s*(?:фт|футов|фут|ft)", s)
    if tm:
        try:
            tele = int(tm.group(1))
        except Exception:
            tele = None
    cleaned = re.sub(r"телепат[а-я\s]*?\d+\s*(?:фт|футов|фут|ft)", "", raw, flags=re.IGNORECASE)
    items = [x.strip().strip('.') for x in cleaned.split(',') if x.strip()]
    return {"items": items, "telepathy_ft": tele, "raw": raw}


def _split_list(s: str) -> List[str]:
    parts: List[str] = []
    for chunk in s.split(','):
        sub = [p.strip() for p in re.split(r"\s+и\s+", chunk) if p.strip()]
        parts.extend(sub)
    return [p for p in [x.strip().strip('.') for x in parts] if p]


def extract_damage_and_conditions(page_text: str) -> Tuple[Dict[str, List[str]], List[str]]:
    damage = {"resistances": [], "immunities": [], "vulnerabilities": []}
    cond_immun: List[str] = []
    m = re.search(r"Иммунитет[ы]?\s+к\s+урон[ау]\s+([^\n]+)", page_text, flags=re.IGNORECASE)
    if m:
        damage["immunities"] = _split_list(m.group(1))
    m = re.search(r"Сопротивлени[ея]\s+урон[ау]?\s+([^\n]+)", page_text, flags=re.IGNORECASE)
    if m:
        damage["resistances"] = _split_list(m.group(1))
    m = re.search(r"Уязвимост[ьи]\с+к\с+урон[ау]\s+([^\n]+)", page_text, flags=re.IGNORECASE)
    if m:
        damage["vulnerabilities"] = _split_list(m.group(1))
    m = re.search(r"Иммунитет[ы]?\s+к\s+состояни[яям]\s+([^\n]+)", page_text, flags=re.IGNORECASE)
    if m:
        cond_immun = _split_list(m.group(1))
    return damage, cond_immun

# New: sources (codes & pages), environment, spellcasting

def extract_sources_and_env(page_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    sources: List[Dict[str, Any]] = []
    environment: List[str] = []
    # sources often appear as like "MM 14" or in the header
    for m in re.finditer(r"\b([A-Z]{2,5})\s*(\d{1,4})\b", page_text):
        code = m.group(1)
        page = int(m.group(2))
        if code in {"MM", "PHB", "DMG", "SRD", "MPMM", "VGM", "XGE", "VRGR", "MTF"}:
            sources.append({"code": code, "page": page})
    # environment: look for line starting with "Местность"
    me = re.search(r"Местност[ьи]\s+обитани[яия]\s+([^\n]+)", page_text, flags=re.IGNORECASE)
    if me:
        environment = _split_list(me.group(1))
    return sources, environment


def extract_spellcasting_blocks(soup: BeautifulSoup) -> Dict[str, Any]:
    res = {"innate": [], "prepared": [], "raw_blocks": []}
    # Find sections mentioning spellcasting
    for header in soup.find_all(["h3", "h4", "h5"]):
        name = header.get_text(strip=True).lower()
        if "заклинан" in name or "колдов" in name or "spellcast" in name:
            block_html = []
            block_plain = []
            current = header.find_next_sibling()
            while current and current.name not in ["h2", "h3", "h4", "h5", "h6"]:
                if current.name in ["p", "ul", "ol", "div", "li"]:
                    block_html.append(str(current))
                    block_plain.append(current.get_text(" ", strip=True))
                current = current.find_next_sibling()
            raw = "\n".join(block_plain).strip()
            if raw:
                res["raw_blocks"].append(raw)
            # naive split by markers for innate/prepared
            if "врожденное" in name or "innate" in name:
                res["innate"].append(raw)
            else:
                res["prepared"].append(raw)
    return res

# ---------------- Block extraction (traits/actions/etc.) -----------------

SECTION_MAP = {
    "черты": "traits",
    "особенности": "traits",
    "действия": "actions",
    "бонусные действия": "bonus_actions",
    "реакции": "reactions",
    "легендарные действия": "legendary_actions",
    "логово": "lair_actions",
    "региональные эффекты": "regional_effects",
}


def extract_blocks(soup: BeautifulSoup) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = {k: [] for k in set(SECTION_MAP.values())}

    for header in soup.find_all(["h3", "h4", "h5"]):
        name = header.get_text(strip=True).lower()
        sec_key = None
        for marker, key in SECTION_MAP.items():
            if marker in name:
                sec_key = key
                break
        if not sec_key:
            continue
        current = header.find_next_sibling()
        while current and current.name not in ["h2", "h3", "h4", "h5", "h6"]:
            if current.name in ["p", "li", "div"]:
                html = str(current)
                plain = current.get_text(" ", strip=True)
                item_name = None
                b = current.find(["b", "strong"]) if hasattr(current, 'find') else None
                if b and b.get_text(strip=True):
                    item_name = b.get_text(strip=True).rstrip(':')
                if not item_name and ':' in plain:
                    item_name = plain.split(':', 1)[0].strip()
                result[sec_key].append({"name": item_name or "", "text_html": html, "text_plain": plain})
            current = current.find_next_sibling()
    return result


def extract_core_fields(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text("\n")

    ru, en = extract_title_ru_en(soup)
    taxonomy = extract_taxonomy(page_text)
    ac = extract_ac(page_text)
    hp = extract_hp(page_text)
    speeds = extract_speed(page_text)
    abilities = extract_abilities(page_text)
    cr = extract_cr(page_text)
    prof = extract_proficiency(page_text)
    saving_throws = extract_saving_throws(page_text)
    skills = extract_skills(page_text)
    senses = extract_senses(page_text)
    languages = extract_languages(page_text)
    damage, cond_immun = extract_damage_and_conditions(page_text)
    blocks = extract_blocks(soup)
    sources, environment = extract_sources_and_env(page_text)
    spellcasting = extract_spellcasting_blocks(soup)

    extracted: Dict[str, Any] = {
        "title": {"ru": ru, "en": en},
        "taxonomy": taxonomy,
        "ac": ac,
        "hp": hp,
        "speeds": speeds,
        "abilities": abilities,
        "saving_throws": saving_throws,
        "skills": skills,
        "senses": senses,
        "languages": languages,
        "damage": damage,
        "condition_immunities": cond_immun,
        "cr": cr,
        "proficiency_bonus": prof,
        "sources": sources,
        "environment": environment,
        "spellcasting": spellcasting,
        **blocks,
    }
    return extracted


def ingest_raw(db_name: str, coll_name: str, uri: str, links: List[Dict[str, str]], limit: int, delay: float) -> Dict[str, int]:
    client = build_mongo_client(uri)
    db = client[db_name]
    coll = db[coll_name]

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36"
    })

    processed = 0
    upserts = 0

    for item in links[: (limit or len(links))]:
        url = item.get("url")
        if not url:
            continue
        try:
            resp = session.get(url)
            resp.raise_for_status()
            html = resp.text
            text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
            content_hash = sha1_text(html)
            now_iso = datetime.utcnow().isoformat() + "Z"

            extracted = extract_core_fields(html)

            doc = {
                "source": {
                    "provider": "dnd.su",
                    "url": url,
                    "slug": slug_from_url(url),
                    "page_codes": []
                },
                "ingest": {
                    "schema_version": 1,
                    "parser_version": "v0.5.0",
                    "fetched_at": now_iso,
                    "content_hash": content_hash
                },
                "raw": {"html": html, "text": text},
                "extracted": extracted,
                "labels": ["dndsu_v1"],
                "diagnostics": {"warnings": [], "errors": []}
            }

            result = coll.update_one({"source.url": url}, {"$set": doc}, upsert=True)
            if result.upserted_id is not None or result.modified_count > 0:
                upserts += 1
            processed += 1
            print(f"[{processed}/{limit or len(links)}] upserted={bool(result.upserted_id)} url={url}")
            if delay and delay > 0:
                time.sleep(delay)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            continue

    client.close()
    return {"processed": processed, "upserts": upserts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="dnd.su tools: crawl links and/or ingest raw pages to Mongo")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://mongo:27017"))
    parser.add_argument("--mongo-db", default=os.getenv("MONGO_DB", "dnd_helper"))
    parser.add_argument("--mongo-collection", default=os.getenv("MONGO_COLLECTION", "raw_monster_dndsu"))

    # crawl options
    parser.add_argument("--crawl-links", action="store_true", help="Crawl dnd.su /bestiary/ links and save cache file")
    parser.add_argument("--base-url", default="https://dnd.su")
    parser.add_argument("--bestiary-url", default="https://dnd.su/bestiary/")
    parser.add_argument("--test-limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--resume-file", default="/app/scripts/monster_parser/output/bestiary_links_cache.json")

    # ingest options
    parser.add_argument("--ingest-raw", action="store_true", help="Fetch pages and upsert raw docs into Mongo")
    parser.add_argument("--ingest-limit", type=int, default=10)

    args = parser.parse_args(argv)

    try:
        if args.crawl_links:
            links = crawl_bestiary_links(args.bestiary_url, args.base_url, args.test_limit, args.delay)
            write_links_cache(args.resume_file, links)
            print(f"Crawled links: {len(links)} → {args.resume_file}")
            return 0

        if args.ingest_raw:
            links = read_links_cache(args.resume_file)
            if not links:
                print("No cache found, crawling...")
                links = crawl_bestiary_links(args.bestiary_url, args.base_url, args.test_limit or args.ingest_limit, args.delay)
                write_links_cache(args.resume_file, links)
            stats = ingest_raw(args.mongo_db, args.mongo_collection, args.mongo_uri, links, args.ingest_limit, args.delay)
            print(f"Ingested: processed={stats['processed']} upserts={stats['upserts']}")
            return 0

        result = upsert_dummy(args.mongo_db, args.mongo_collection, args.mongo_uri)
        print(f"Upsert result: matched={result['matched']} modified={result['modified']} upserted_id={result['upserted_id']}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
