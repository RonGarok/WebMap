import json
import time
import os
from steam_query import MasterServer, A2SInfo

OUTPUT_FILE = "webgame.json"
MAX_NEW_PER_SESSION = 100

# Jeux Steam (app IDs)
GAMES = {
    "rust": 252490,
    "arkse": 346110,
    "cs2": 730,
    "csgo": 730,
    "tf2": 440,
    "unturned": 304930,
    "squad": 393380,
    "dayz": 221100,
    "valheim": 892970,
    "palworld": 1623730
}

CENTRAL_NODE = {
    "id": "webmap",
    "name": "WebMap Central",
    "favicon": "https://webmap/assets/favicon.png",
    "x": 0,
    "y": 0
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


def fetch_server_list(app_id):
    print(f"Fetching server list for app {app_id}...")
    ms = MasterServer()
    servers = ms.query(appid=app_id)
    print(f"Found {len(servers)} servers")
    return servers


def query_server(ip, port, game):
    try:
        info = A2SInfo(ip, port).get_dict()

        return {
            "id": f"{ip}:{port}",
            "ip": ip,
            "port": port,
            "game": game,
            "name": info.get("name", "Unknown"),
            "players": info.get("players", 0),
            "max_players": info.get("max_players", 0),
            "map": info.get("map", "Unknown"),
            "country": "??",
            "ping": info.get("ping", 0),
            "tags": [],
            "last_seen": int(time.time()),
            "x": None,
            "y": None
        }

    except Exception:
        return None


def update_database():
    db = load_existing()
    existing = {s["id"]: s for s in db["servers"]}
    queue = db.get("queue", [])

    new_servers = {}
    new_count = 0

    for game, app_id in GAMES.items():
        server_list = fetch_server_list(app_id)

        for ip, port in server_list:
            sid = f"{ip}:{port}"

            if sid not in existing and sid not in new_servers:
                if new_count >= MAX_NEW_PER_SESSION:
                    queue.append({"ip": ip, "port": port, "game": game})
                    continue

                srv = query_server(ip, port, game)
                if srv:
                    new_servers[sid] = srv
                    new_count += 1
            else:
                srv = query_server(ip, port, game)
                if srv:
                    new_servers[sid] = srv

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
