import requests
from bs4 import BeautifulSoup
import json
import time
import os
import random

# Jeux à scraper (tu peux en enlever/ajouter)
GAMES = {
    "cs2": "https://www.gametracker.com/search/cs2/?searchpge=1#search",
    "csgo": "https://www.gametracker.com/search/csgo/?searchpge=1#search",
    "minecraft": "https://www.gametracker.com/search/minecraft/?searchpge=1#search",
    "rust": "https://www.gametracker.com/search/rust/?searchpge=1#search"
}

OUTPUT_FILE = "webgame.json"

CENTRAL_NODE = {
    "id": "webmap",
    "name": "WebMap Central",
    "favicon": "https://webmap/assets/favicon.png",
    "x": 0,
    "y": 0
}

MAX_NEW_PER_SESSION = 100

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://www.gametracker.com/",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "gt_cookie_accept=1"
}


def fetch_html(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200 and "table_lst" in resp.text:
                return resp.text
            else:
                print(f"[{attempt+1}/{retries}] HTTP {resp.status_code} or no table, retrying...")
        except Exception as e:
            print(f"[{attempt+1}/{retries}] Request error: {e}")
        time.sleep(delay + random.uniform(0, 1))
    print("Failed to fetch:", url)
    return ""


def parse_server_row(row, game):
    cols = row.find_all("td")
    if len(cols) < 5:
        return None

    ip_port = cols[0].text.strip()
    if ":" not in ip_port:
        return None
    ip, port = ip_port.split(":")

    name = cols[1].text.strip()

    players_raw = cols[2].text.strip()
    if "/" in players_raw:
        try:
            players, max_players = players_raw.split("/")
            players = int(players)
            max_players = int(max_players)
        except:
            players = 0
            max_players = 0
    else:
        players = 0
        max_players = 0

    map_name = cols[3].text.strip()
    country = cols[4].text.strip()

    ping = 0
    if len(cols) > 5:
        try:
            ping = int(cols[5].text.strip())
        except:
            ping = 0

    return {
        "id": f"{ip}:{port}",
        "ip": ip,
        "port": int(port),
        "game": game,
        "name": name,
        "players": players,
        "max_players": max_players,
        "map": map_name,
        "country": country,
        "ping": ping,
        "tags": [],
        "last_seen": int(time.time()),
        "x": None,
        "y": None
    }


def scrape_game(game, url):
    print(f"Scraping {game}...")
    servers = []

    html = fetch_html(url)
    if not html:
        print(f"No HTML for {game}")
        return servers

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "table_lst"})
    if not table:
        print(f"No table found for {game}")
        return servers

    rows = table.find_all("tr")[1:]

    for row in rows:
        server = parse_server_row(row, game)
        if server:
            servers.append(server)

    print(f"Found {len(servers)} servers for {game}")
    return servers


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


def update_database():
    db = load_existing()

    existing = {s["id"]: s for s in db["servers"]}
    queue = db.get("queue", [])

    new_servers = {}
    new_count = 0

    for game, url in GAMES.items():
        scraped = scrape_game(game, url)

        for s in scraped:
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
            print("Limite de 100 nouveaux serveurs atteinte, arrêt de la session.")
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
    print(f"Session: {new_count} nouveaux serveurs, {len(queue)} en attente, {len(merged)} au total.")


if __name__ == "__main__":
    update_database()
