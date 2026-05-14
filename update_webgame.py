import requests
import json
import time
import os

OUTPUT_FILE = "webgame.json"
MAX_NEW_PER_SESSION = 100

# Tu pourras ajouter autant de jeux que tu veux ici
GAMES = [
    "rust",
    "arkse",
    "dayz",
    "scum",
    "pz",
    "squad",
    "7daystodie",
    "valheim",
    "palworld"
]

CENTRAL_NODE = {
    "id": "webmap",
    "name": "WebMap Central",
    "favicon": "https://webmap/assets/favicon.png",
    "x": 0,
    "y": 0
}

API_BASE = "https://api.battlemetrics.com/servers"


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


def fetch_servers_for_game(game, max_pages=5):
    servers = []
    for page in range(1, max_pages + 1):
        url = f"{API_BASE}?filter[game]={game}&page[size]=50&page[number]={page}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                print(f"Error {r.status_code} for {game} page {page}")
                break

            data = r.json()
            if "data" not in data:
                break

            for srv in data["data"]:
                attr = srv["attributes"]
                servers.append({
                    "id": srv["id"],
                    "ip": attr.get("ip", None),
                    "port": attr.get("port", None),
                    "game": game,
                    "name": attr.get("name", "Unknown"),
                    "players": attr.get("players", 0),
                    "max_players": attr.get("maxPlayers", 0),
                    "country": attr.get("country", "??"),
                    "map": attr.get("details", {}).get("map", "Unknown"),
                    "ping": attr.get("ping", 0),
                    "tags": attr.get("details", {}).get("tags", []),
                    "last_seen": int(time.time()),
                    "x": None,
                    "y": None
                })

        except Exception as e:
            print("Error:", e)
            break

    print(f"{game}: {len(servers)} servers fetched")
    return servers


def update_database():
    db = load_existing()

    existing = {s["id"]: s for s in db["servers"]}
    queue = db.get("queue", [])

    new_servers = {}
    new_count = 0

    # 1) Fetch servers from BattleMetrics
    for game in GAMES:
        fetched = fetch_servers_for_game(game)

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

    # 2) Merge
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

    # 3) Edges → central
    db["edges"] = [
        ["webmap", srv["id"]] for srv in merged
    ]

    save_json(db)
    print(f"Session: {new_count} nouveaux serveurs, {len(queue)} en attente, {len(merged)} total.")


if __name__ == "__main__":
    update_database()
