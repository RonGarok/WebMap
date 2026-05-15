import json
import os
import time
import socket
import random
import requests

OUTPUT_FILE = "webmachine.json"
MAX_NEW_PER_SESSION = 500

PROVIDERS = {
    "cloudflare": {
        "asn": 13335,
        "name": "Cloudflare"
    },
    "ovh": {
        "asn": 16276,
        "name": "OVH"
    },
    "google": {
        "asn": 15169,
        "name": "Google"
    },
    "microsoft": {
        "asn": 8075,
        "name": "Microsoft"
    }
    # Tu pourras en rajouter d'autres
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
            "machines": [],
            "edges": [],
            "queue": []
        }
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def fetch_prefixes_for_asn(asn):
    url = f"https://api.bgpview.io/asn/{asn}/prefixes"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"ASN {asn}: HTTP {r.status_code}")
            return []
        data = r.json()
        prefixes = []

        for p in data.get("data", {}).get("ipv4_prefixes", []):
            prefixes.append(p["prefix"])

        print(f"ASN {asn}: {len(prefixes)} prefixes")
        return prefixes
    except Exception as e:
        print(f"ASN {asn}: error {e}")
        return []


def sample_ips_from_prefix(prefix, max_samples=3):
    # prefix format: "1.2.3.0/24"
    try:
        ip_part, cidr = prefix.split("/")
        octets = ip_part.split(".")
        if len(octets) != 4:
            return []

        base = [int(o) for o in octets]
        ips = set()

        # On ne fait que des /24 simples, sinon on échantillonne grossièrement
        for _ in range(max_samples * 3):
            last = random.randint(1, 254)
            ip = f"{base[0]}.{base[1]}.{base[2]}.{last}"
            ips.add(ip)
            if len(ips) >= max_samples:
                break

        return list(ips)
    except:
        return []


def reverse_dns(ip):
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except:
        return None


def scan_ports(ip, ports=(80, 443), timeout=0.5):
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


def build_machine(ip, provider_name, asn, hostname, open_ports):
    services = []
    if 80 in open_ports:
        services.append("http")
    if 443 in open_ports:
        services.append("https")

    return {
        "id": ip,
        "ip": ip,
        "asn": f"AS{asn}",
        "provider": provider_name,
        "hostname": hostname or "",
        "country": "??",
        "ports": open_ports,
        "services": services,
        "last_seen": int(time.time()),
        "x": None,
        "y": None
    }


def update_database():
    db = load_existing()

    existing = {m["id"]: m for m in db["machines"]}
    queue = db.get("queue", [])

    new_machines = {}
    new_count = 0

    # 1) Traiter d'abord la queue
    random.shuffle(queue)
    new_queue = []

    for item in queue:
        if new_count >= MAX_NEW_PER_SESSION:
            new_queue.append(item)
            continue

        ip = item["ip"]
        provider_name = item["provider"]
        asn = item["asn"]

        if ip in existing or ip in new_machines:
            continue

        hostname = reverse_dns(ip)
        open_ports = scan_ports(ip)

        if not open_ports and not hostname:
            continue

        machine = build_machine(ip, provider_name, asn, hostname, open_ports)
        new_machines[ip] = machine
        new_count += 1

    # 2) Ajouter de nouvelles IP depuis les ASN
    if new_count < MAX_NEW_PER_SESSION:
        for key, info in PROVIDERS.items():
            asn = info["asn"]
            provider_name = info["name"]

            prefixes = fetch_prefixes_for_asn(asn)
            random.shuffle(prefixes)

            for prefix in prefixes:
                if new_count >= MAX_NEW_PER_SESSION:
                    break

                ips = sample_ips_from_prefix(prefix, max_samples=2)
                for ip in ips:
                    if new_count >= MAX_NEW_PER_SESSION:
                        break

                    if ip in existing or ip in new_machines:
                        continue

                    # On met d'abord en queue, on ne fait pas tout en direct
                    queue_item = {
                        "ip": ip,
                        "provider": provider_name,
                        "asn": asn
                    }
                    new_queue.append(queue_item)

            if new_count >= MAX_NEW_PER_SESSION:
                break

    # Fusion
    merged = []
    for mid, m in new_machines.items():
        if mid in existing:
            old = existing[mid]
            old.update(m)
            merged.append(old)
        else:
            merged.append(m)

    # Ajouter les anciens non mis à jour
    for mid, m in existing.items():
        if mid not in new_machines:
            merged.append(m)

    db["machines"] = merged
    db["queue"] = new_queue

    # Edges :
    edges = []

    # central → ASN
    for key, info in PROVIDERS.items():
        asn_id = f"AS{info['asn']}"
        edges.append(["webmap", asn_id])

    # ASN → machines
    for m in merged:
        edges.append([m["asn"], m["id"]])

    db["edges"] = edges

    save_json(db)
    print(f"Session: {new_count} nouvelles machines, {len(new_queue)} en attente, {len(merged)} total.")


if __name__ == "__main__":
    update_database()
