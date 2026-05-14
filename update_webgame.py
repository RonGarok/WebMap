import requests
from bs4 import BeautifulSoup
import json
import time
import os
import random

OUTPUT_FILE = "webgame.json"
MAX_NEW_PER_SESSION = 100

# Tu pourras ajouter d'autres jeux ici en copiant le pattern
GAMES = {
    "rust": "https://www.battlemetrics.com/servers/rust",
    "arkse": "https://www.battlemetrics.com/servers/arkse",
    "dayz": "https://www.battlemetrics.com/servers/dayz",
    "scum": "https://www.battlemetrics.com/servers/scum",
    "pz": "https://www.battlemetrics.com/servers/pz",
    "squad": "https://www.battlemetrics.com/servers/squad",
    "7daystodie": "https://www.battlemetrics.com/servers/7daystodie",
    "valheim": "https://www.battlemetrics.com/servers/valheim",
    "palworld": "https://www.battlemetrics.com/servers/palworld"
}

CENTRAL_NODE = {
    "id": "webmap",
    "name": "WebMap Central",
    "favicon": "https://webmap/assets/favicon.png",
    "x": 0,
    "y": 0
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}


def load_existing():
    if not os.path.exists(OUTPUT_FILE):
        return {
            "central": CENTRAL_NODE,
            "servers": [],
            "edges": [],
            "queue": []
        }

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def fetch_html(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return r.text
            else:
                print(f"[{attempt+1}/{retries}] HTTP {r.status_code} for {url}")
        except Exception as e:
            print(f"[{attempt+1}/{retries}] Error {e} for {url}")
        time.sleep(delay + random.uniform(0, 1))
    print("Failed to fetch:", url)
    return ""


def parse_server_row(row, game):
    cols = row.find_all("td")
    if len(cols) < 5:
        return None

    # Col 0: Name
    name = cols[0].get_text(strip=True)

    # Col 1: Address (IP:Port)
    addr = cols[1].get_text(strip=True)
    if ":" not in addr:
        return None
    ip, port = addr.split(":", 1)

    # Col 2: Players
    players_raw = cols[2].get_text(strip=True)
    players = 0
    max_players = 0
    if "/" in players_raw:
        try:
            p, m = players_raw.split("/", 1)
            players = int(p.strip())
            max_players = int(m.strip())
        except:
            pass

    # Col 3: Ping
    ping = 0
    try:
        ping = int(cols[3].get_text(strip=True))
    except:
        ping = 0

    # Col 4: Country (flag alt or text)
    country = cols[4].get_text(strip=True)
    if not country:
        img = cols[4].find("img")
        if img and img.get("alt"):
            country = img["alt"].strip()

    return {
        "id": f"{ip}:{port}",
        "ip": ip,
        "port": int(port),
        "game": game,
        "name": name,
        "players": players,
        "max_players": max_players,
        "country": country or "??",
        "map": "Unknown",
        "ping": ping,
        "tags": [],
        "last_seen": int(time.time()),
        "x": None,
        "y": None
    }


def scrape_game(game, url, max_pages=3):
    print(f"Scraping {game}...")
    servers = []

    for page in range(1, max_pages + 1):
        page_url = f"{url}?page={page}"
        html = fetch_html(page_url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"class": "table table-striped table-hover table-sm servers-table"})
        if not table:
            print(f"No table for {game} page {page}")
            break

        rows = table.find("tbody").find_all("tr")
        if not rows:
            break

        for row in rows:
            srv = parse_server_row(row, game)
            if srv:
                servers.append(srv)

    print(f"{game}: {len(servers)} servers fetched")
    return servers


def update_database():
    db = load_existing()

    existing = {s["id"]: s for s in db["servers"]}
    queue = db.get("queue", [])

    new_servers = {}
    new_count = 0

    for game, url in GAMES.items():
        fetched = scrape_game(game, url)

        for s in fetched:
            sid = s["id"]

            if sid not in existing and sid not in new_servers:
                if new_count < MAX_NEW_PER_SESSION:
                    new_servers[sid] = s
                    new_count += 1
                else:
                    queue.append(s)
                    continue
            else:
                new_servers[sid] = s

        if new_count >= MAX_NEW_PER_SESSION:
            print("Limite de 100 nouveaux serveurs atteinte.")
            break

    merged = []
    for sid, srv in new_servers.items():
        if sid in existing:
            old = existing[sid]
            old.update(srv)
            merged.append(old)
        else:
            merged.append(srv)

    db["servers"] = merged
    db["queue"] = queue

    db["edges"] = [
        ["webmap", srv["id"]] for srv in merged
    ]

    save_json(db)
    print(f"Session: {new_count} nouveaux serveurs, {len(queue)} en attente, {len(merged)} total.")


if __name__ == "__main__":
    update_database()
