import requests
from bs4 import BeautifulSoup
import json
import time
import os

# Jeux à scraper
GAMES = {
    "7daystodie": "https://www.gametracker.com/search/7daystodie/?searchpge=1#search",
    "ark": "https://www.gametracker.com/search/ark/?searchpge=1#search",
    "arma2": "https://www.gametracker.com/search/arma2/?searchpge=1#search",
    "arma3": "https://www.gametracker.com/search/arma3/?searchpge=1#search",
    "battlefield2": "https://www.gametracker.com/search/bf2/?searchpge=1#search",
    "battlefield2142": "https://www.gametracker.com/search/bf2142/?searchpge=1#search",
    "battlefield3": "https://www.gametracker.com/search/bf3/?searchpge=1#search",
    "battlefield4": "https://www.gametracker.com/search/bf4/?searchpge=1#search",
    "battlefieldbadcompany2": "https://www.gametracker.com/search/bc2/?searchpge=1#search",
    "callofduty": "https://www.gametracker.com/search/cod/?searchpge=1#search",
    "cod2": "https://www.gametracker.com/search/cod2/?searchpge=1#search",
    "cod4": "https://www.gametracker.com/search/cod4/?searchpge=1#search",
    "codmw2": "https://www.gametracker.com/search/mw2/?searchpge=1#search",
    "codwaw": "https://www.gametracker.com/search/codwaw/?searchpge=1#search",
    "codbo2": "https://www.gametracker.com/search/bo2/?searchpge=1#search",
    "counterstrike": "https://www.gametracker.com/search/cs/?searchpge=1#search",
    "conditionzero": "https://www.gametracker.com/search/cscz/?searchpge=1#search",
    "cssource": "https://www.gametracker.com/search/css/?searchpge=1#search",
    "csgo": "https://www.gametracker.com/search/csgo/?searchpge=1#search",
    "cs2": "https://www.gametracker.com/search/cs2/?searchpge=1#search",
    "dayofdefeat": "https://www.gametracker.com/search/dods/?searchpge=1#search",
    "dayz": "https://www.gametracker.com/search/dayz/?searchpge=1#search",
    "dayzsa": "https://www.gametracker.com/search/dayzsa/?searchpge=1#search",
    "dodsource": "https://www.gametracker.com/search/dods/?searchpge=1#search",
    "dontstarvetogether": "https://www.gametracker.com/search/dst/?searchpge=1#search",
    "eco": "https://www.gametracker.com/search/eco/?searchpge=1#search",
    "factorio": "https://www.gametracker.com/search/factorio/?searchpge=1#search",
    "garrysmod": "https://www.gametracker.com/search/gmod/?searchpge=1#search",
    "halo": "https://www.gametracker.com/search/halo/?searchpge=1#search",
    "haloce": "https://www.gametracker.com/search/haloce/?searchpge=1#search",
    "insurgency": "https://www.gametracker.com/search/insurgency/?searchpge=1#search",
    "insurgencysandstorm": "https://www.gametracker.com/search/sandstorm/?searchpge=1#search",
    "killingfloor": "https://www.gametracker.com/search/kf/?searchpge=1#search",
    "killingfloor2": "https://www.gametracker.com/search/kf2/?searchpge=1#search",
    "left4dead": "https://www.gametracker.com/search/l4d/?searchpge=1#search",
    "left4dead2": "https://www.gametracker.com/search/l4d2/?searchpge=1#search",
    "minecraft": "https://www.gametracker.com/search/minecraft/?searchpge=1#search",
    "mordhau": "https://www.gametracker.com/search/mordhau/?searchpge=1#search",
    "naturalselection2": "https://www.gametracker.com/search/ns2/?searchpge=1#search",
    "palworld": "https://www.gametracker.com/search/palworld/?searchpge=1#search",
    "projectzomboid": "https://www.gametracker.com/search/zomboid/?searchpge=1#search",
    "quake2": "https://www.gametracker.com/search/q2/?searchpge=1#search",
    "quake3": "https://www.gametracker.com/search/q3/?searchpge=1#search",
    "quake4": "https://www.gametracker.com/search/q4/?searchpge=1#search",
    "ragemp": "https://www.gametracker.com/search/ragemp/?searchpge=1#search",
    "redm": "https://www.gametracker.com/search/redm/?searchpge=1#search",
    "rfactor2": "https://www.gametracker.com/search/rfactor2/?searchpge=1#search",
    "rust": "https://www.gametracker.com/search/rust/?searchpge=1#search",
    "samp": "https://www.gametracker.com/search/samp/?searchpge=1#search",
    "scpsl": "https://www.gametracker.com/search/scpsl/?searchpge=1#search",
    "serioussam": "https://www.gametracker.com/search/serioussam/?searchpge=1#search",
    "serioussam2": "https://www.gametracker.com/search/serioussam2/?searchpge=1#search",
    "spaceengineers": "https://www.gametracker.com/search/spaceengineers/?searchpge=1#search",
    "squad": "https://www.gametracker.com/search/squad/?searchpge=1#search",
    "starbound": "https://www.gametracker.com/search/starbound/?searchpge=1#search",
    "teamfortress2": "https://www.gametracker.com/search/tf2/?searchpge=1#search",
    "teamspeak3": "https://www.gametracker.com/search/ts3/?searchpge=1#search",
    "terraria": "https://www.gametracker.com/search/terraria/?searchpge=1#search",
    "theforest": "https://www.gametracker.com/search/theforest/?searchpge=1#search",
    "unturned": "https://www.gametracker.com/search/unturned/?searchpge=1#search",
    "valheim": "https://www.gametracker.com/search/valheim/?searchpge=1#search",
    "ventrilo": "https://www.gametracker.com/search/ventrilo/?searchpge=1#search",
    "warsow": "https://www.gametracker.com/search/warsow/?searchpge=1#search",
    "wolfensteinenemyterritory": "https://www.gametracker.com/search/wet/?searchpge=1#search",
    "zandronum": "https://www.gametracker.com/search/zandronum/?searchpge=1#search"
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
        players, max_players = players_raw.split("/")
        players = int(players)
        max_players = int(max_players)
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

    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
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

    # 1) Scrape + limiter à 100 nouveaux serveurs
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
            print("Limite de 100 nouveaux serveurs atteinte.")
            break

    # 2) Fusion propre
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

    # 3) Edges → chaque serveur vers le node central
    db["edges"] = [
        ["webmap", srv["id"]] for srv in merged
    ]

    save_json(db)
    print(f"Session: {new_count} nouveaux serveurs, {len(queue)} en attente.")


if __name__ == "__main__":
    update_database()
