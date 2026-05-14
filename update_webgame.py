import socket
import struct
import json
import time
import os

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


# ---------------------------
# MASTER SERVER QUERY (UDP)
# ---------------------------

def fetch_server_list(app_id):
    print(f"Fetching server list for app {app_id}...")

    ms = ("208.64.200.39", 27011)  # master.steampowered.com
    q = b"\x31" + b"\xff" * 4 + f"\\appid\\{app_id}\\noplayers\\1".encode() + b"\x00"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    sock.sendto(q, ms)

    servers = []

    while True:
        try:
            data, _ = sock.recvfrom(1400)
        except socket.timeout:
            break

        if not data.startswith(b"\xff\xff\xff\xff"):
            break

        payload = data[6:]
        if payload == b"EOT\x00":
            break

        for i in range(0, len(payload), 6):
            ip = ".".join(str(b) for b in payload[i:i+4])
            port = struct.unpack(">H", payload[i+4:i+6])[0]
            servers.append((ip, port))

    print(f"Found {len(servers)} servers")
    return servers


# ---------------------------
# A2S_INFO (UDP)
# ---------------------------

def query_server(ip, port, game):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.5)

        packet = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00"
        sock.sendto(packet, (ip, port))

        data, _ = sock.recvfrom(4096)

        if not data.startswith(b"\xFF\xFF\xFF\xFFI"):
            return None

        # Skip header
        data = data[6:]

        def read_string(data):
            end = data.find(b"\x00")
            return data[:end].decode(errors="ignore"), data[end+1:]

        name, data = read_string(data)
        map_name, data = read_string(data)
        folder, data = read_string(data)
        game_name, data = read_string(data)

        # Skip rest
        return {
            "id": f"{ip}:{port}",
            "ip": ip,
            "port": port,
            "game": game,
            "name": name,
            "players": 0,
            "max_players": 0,
            "map": map_name,
            "country": "??",
            "ping": 0,
            "tags": [],
            "last_seen": int(time.time()),
            "x": None,
            "y": None
        }

    except Exception:
        return None


# ---------------------------
# MAIN UPDATE LOGIC
# ---------------------------

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
