import json
import os
import time
import socket
import random
import sys

OUTPUT_FILE = "webmachine.json"
PREFIX_FILE = "asn_prefixes.txt"
MAX_NEW_PER_SESSION = 1000

CENTRAL_NODE = {
    "id": "webmap",
    "name": "WebMap Central",
    "favicon": "https://webmap.ct.ws/assets/favicon.png",
    "x": 0,
    "y": 0
}

# ---------------------------------------------------------
# LOAD ASN PREFIXES
# ---------------------------------------------------------
def load_prefixes():
    prefixes = {}
    if not os.path.exists(PREFIX_FILE):
        print("asn_prefixes.txt introuvable !")
        return prefixes

    with open(PREFIX_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            asn, prefix = line.split("|")
            prefixes.setdefault(asn, []).append(prefix)

    print(f"Chargé {sum(len(v) for v in prefixes.values())} prefixes ASN.")
    return prefixes


# ---------------------------------------------------------
# LOAD EXISTING JSON
# ---------------------------------------------------------
def load_existing():
    if not os.path.exists(OUTPUT_FILE):
        return {
            "central": CENTRAL_NODE,
            "machines": [],
            "edges": [],
            "queue": []
        }
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------
# SAVE JSON
# ---------------------------------------------------------
def save_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ---------------------------------------------------------
# SAMPLE IPs FROM PREFIX
# ---------------------------------------------------------
def sample_ips(prefix, count=3):
    try:
        ip_part, cidr = prefix.split("/")
        octets = ip_part.split(".")
        base = [int(o) for o in octets]

        ips = set()
        for _ in range(count * 4):
            last = random.randint(1, 254)
            ip = f"{base[0]}.{base[1]}.{base[2]}.{last}"
            ips.add(ip)
            if len(ips) >= count:
                break

        return list(ips)
    except:
        return []


# ---------------------------------------------------------
# PROPAGATION : générer de nouvelles IP à partir d'une IP
# ---------------------------------------------------------
def propagate_from_ip(ip, count=3):
    try:
        a, b, c, d = ip.split(".")
        base = f"{a}.{b}.{c}"
        ips = []
        for _ in range(count):
            last = random.randint(1, 254)
            ips.append(f"{base}.{last}")
        return ips
    except:
        return []


# ---------------------------------------------------------
# REVERSE DNS
# ---------------------------------------------------------
def reverse_dns(ip):
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except:
        return None


# ---------------------------------------------------------
# PORT SCAN
# ---------------------------------------------------------
def scan_ports(ip, ports=(80, 443, 22, 3389, 25, 53), timeout=0.4):
    open_ports = []
    for port in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                open_ports.append(port)
            s.close()
        except:
            pass
    return open_ports


# ---------------------------------------------------------
# BUILD MACHINE OBJECT
# ---------------------------------------------------------
def build_machine(ip, asn, hostname, open_ports):
    if 3389 in open_ports:
        os_guess = "windows"
    elif 22 in open_ports:
        os_guess = "linux"
    else:
        os_guess = "unknown"

    return {
        "id": ip,
        "ip": ip,
        "asn": asn,
        "provider": asn,
        "hostname": hostname or "",
        "country": "??",
        "ports": open_ports,
        "services": [],
        "os": os_guess,
        "favicon": None,
        "last_seen": int(time.time()),
        "x": random.randint(-5000, 5000),
        "y": random.randint(-5000, 5000)
    }


# ---------------------------------------------------------
# MAIN UPDATE
# ---------------------------------------------------------
def update_database():
    prefixes = load_prefixes()
    db = load_existing()

    existing = {m["id"]: m for m in db["machines"]}
    queue = db.get("queue", [])

    new_machines = {}
    new_count = 0
    new_queue = []

    print("\n=== TRAITEMENT DE LA QUEUE ===")

    try:
        # -----------------------------------------------------
        # 1) PROCESS QUEUE FIRST
        # -----------------------------------------------------
        random.shuffle(queue)

        for item in queue:
            if new_count >= MAX_NEW_PER_SESSION:
                break

            ip = item["ip"]
            asn = item["asn"]

            if ip in existing or ip in new_machines:
                continue

            hostname = reverse_dns(ip)
            open_ports = scan_ports(ip)

            if not open_ports and not hostname:
                continue

            machine = build_machine(ip, asn, hostname, open_ports)
            new_machines[ip] = machine
            new_count += 1

            # LOG toutes les 10 machines
            if new_count % 10 == 0:
                print(f"[QUEUE] {new_count}/499 → {ip} ({asn})")

            # PROPAGATION : ajouter nouvelles IP
            for new_ip in propagate_from_ip(ip, count=2):
                new_queue.append({"ip": new_ip, "asn": asn})

        # -----------------------------------------------------
        # 2) IF STILL SPACE → ADD NEW IPs FROM PREFIXES
        # -----------------------------------------------------
        print("\n=== AJOUT DE NOUVELLES IPS ===")

        if new_count < MAX_NEW_PER_SESSION:
            for asn, prefix_list in prefixes.items():
                for prefix in prefix_list:
                    if new_count >= MAX_NEW_PER_SESSION:
                        break

                    ips = sample_ips(prefix, count=3)
                    for ip in ips:
                        if ip in existing or ip in new_machines:
                            continue

                        new_queue.append({"ip": ip, "asn": asn})

                        if len(new_queue) % 50 == 0:
                            print(f"[QUEUE GEN] {len(new_queue)} IP générées… dernier prefix {asn}:{prefix}")

    except KeyboardInterrupt:
        print("\n\n=== CTRL+C détecté → arrêt propre ===")

    # -----------------------------------------------------
    # MERGE MACHINES
    # -----------------------------------------------------
    merged = []

    for mid, m in new_machines.items():
        if mid in existing:
            old = existing[mid]
            old.update(m)
            merged.append(old)
        else:
            merged.append(m)

    for mid, m in existing.items():
        if mid not in new_machines:
            merged.append(m)

    db["machines"] = merged
    db["queue"] = new_queue

    # -----------------------------------------------------
    # BUILD EDGES
    # -----------------------------------------------------
    edges = []

    for asn in prefixes.keys():
        edges.append(["webmap", asn])

    for m in merged:
        edges.append([m["asn"], m["id"]])

    db["edges"] = edges

    save_json(db)

    print(f"\n=== FIN DE SESSION ===")
    print(f"Machines ajoutées : {new_count}")
    print(f"Queue restante : {len(new_queue)}")
    print(f"Total machines : {len(merged)}")


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------
if __name__ == "__main__":
    update_database()
