import json
import os
import time
import socket
import random
import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = "webmachine.json"
MAX_NEW_PER_SESSION = 500

PROVIDERS = {
    "cloudflare": {"asn": 13335, "name": "Cloudflare"},
    "ovh": {"asn": 16276, "name": "OVH"},
    "google": {"asn": 15169, "name": "Google"},
    "microsoft": {"asn": 8075, "name": "Microsoft"},
    "amazon": {"asn": 16509, "name": "Amazon AWS"},
    "hetzner": {"asn": 24940, "name": "Hetzner"}
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
        return {"central": CENTRAL_NODE, "machines": [], "edges": [], "queue": []}
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --------------------------
# FLATICON LOGO SCRAPER
# --------------------------
def find_provider_logo(provider_name):
    try:
        url = f"https://www.flaticon.com/search?word={provider_name}"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        img = soup.find("img", {"class": "lzy"})

        if not img:
            return None

        return img.get("data-src") or img.get("src")
    except:
        return None

# --------------------------
# ASN PREFIX FETCH
# --------------------------
def fetch_prefixes_for_asn(asn):
    url = f"https://api.bgpview.io/asn/{asn}/prefixes"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        prefixes = [p["prefix"] for p in data.get("data", {}).get("ipv4_prefixes", [])]
        return prefixes
    except:
        return []

# --------------------------
# IP SAMPLING
# --------------------------
def sample_ips_from_prefix(prefix, max_samples=3):
    try:
        ip_part, cidr = prefix.split("/")
        octets = ip_part.split(".")
        base = [int(o) for o in octets]
        ips = set()

        for _ in range(max_samples * 3):
            last = random.randint(1, 254)
            ip = f"{base[0]}.{base[1]}.{base[2]}.{last}"
            ips.add(ip)
            if len(ips) >= max_samples:
                break

        return list(ips)
    except:
        return []

# --------------------------
# REVERSE DNS
# --------------------------
def reverse_dns(ip):
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except:
        return None

# --------------------------
# PORT SCAN
# --------------------------
def scan_ports(ip, ports=(80, 443, 22, 3389, 25, 53), timeout=0.5):
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

# --------------------------
# MACHINE BUILDER
# --------------------------
def build_machine(ip, provider_name, asn, hostname, open_ports):
    services = []
    if 80 in open_ports: services.append("http")
    if 443 in open_ports: services.append("https")
    if 22 in open_ports: services.append("ssh")
    if 3389 in open_ports: services.append("rdp")
    if 25 in open_ports: services.append("mail")
    if 53 in open_ports: services.append("dns")

    # OS detection (simple)
    if 3389 in open_ports:
        os_guess = "windows"
    elif 22 in open_ports:
        os_guess = "linux"
    elif provider_name.lower() in ["cloudflare", "google", "amazon"]:
        os_guess = "edge-cdn"
    else:
        os_guess = "unknown"

    # Flaticon logo
    logo = find_provider_logo(provider_name.lower())

    return {
        "id": ip,
        "ip": ip,
        "asn": f"AS{asn}",
        "provider": provider_name,
        "hostname": hostname or "",
        "country": "??",
        "ports": open_ports,
        "services": services,
        "os": os_guess,
        "favicon": logo,
        "last_seen": int(time.time()),
        "x": None,
        "y": None
    }

# --------------------------
# MAIN UPDATE
# --------------------------
def update_database():
    db = load_existing()
    existing = {m["id"]: m for m in db["machines"]}
    queue = db.get("queue", [])

    new_machines = {}
    new_count = 0
    new_queue = []

    # 1) Process queue
    random.shuffle(queue)
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

    # 2) Add new IPs from ASN prefixes
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
                    if ip in existing or ip in new_machines:
                        continue

                    new_queue.append({"ip": ip, "provider": provider_name, "asn": asn})

    # Merge
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

    # Edges
    edges = []
    for key, info in PROVIDERS.items():
        edges.append(["webmap", f"AS{info['asn']}"])

    for m in merged:
        edges.append([m["asn"], m["id"]])

    db["edges"] = edges

    save_json(db)
    print(f"Session: {new_count} nouvelles machines, {len(new_queue)} en attente, {len(merged)} total.")

if __name__ == "__main__":
    update_database()
