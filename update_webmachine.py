#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
 WebMachine V2
---------------------------------------------------------
 Intelligent infrastructure crawler
=========================================================

Features:
- Smart propagation
- Banner analysis
- TLS probing
- RDP probing
- SMTP probing
- SSH probing
- OS fingerprinting
- ASN validation
- Honeypot filtering
- CDN filtering
- JSON export
=========================================================
"""

import ipaddress
import json
import os
import queue
import random
import socket
import ssl
import struct
import subprocess
import time
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

OUTPUT_FILE = "webmachine_v2.json"
PREFIX_FILE = "asn_prefixes.txt"

MAX_NEW_PER_RUN = 1000

CONNECT_TIMEOUT = 1.2
READ_TIMEOUT = 1.5

COMMON_PORTS = [
    21, 22, 23, 25,
    53, 80, 110, 143,
    443, 465, 587,
    993, 995,
    3389,
    8080, 8443
]

PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16")
]

KNOWN_CDN_KEYWORDS = [
    "cloudflare",
    "akamai",
    "fastly",
    "cloudfront",
    "edgekey",
    "cdn",
    "cache"
]

KNOWN_ROUTER_KEYWORDS = [
    "router",
    "gateway",
    "gw.",
    "bras",
    "core",
    "edge",
    "crs",
    "pe-",
]

# =========================================================
# UTILS
# =========================================================

def log(msg):
    now = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")


def now_ts():
    return int(time.time())


def is_private_ip(ip):
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in PRIVATE_NETWORKS)
    except Exception:
        return True


def safe_recv(sock, size=1024):
    try:
        sock.settimeout(READ_TIMEOUT)
        return sock.recv(size)
    except Exception:
        return b""


# =========================================================
# ASN PREFIX LOADING
# =========================================================

def load_prefixes():
    prefixes = {}

    if not os.path.exists(PREFIX_FILE):
        log("Prefix file missing.")
        return prefixes

    with open(PREFIX_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if "|" not in line:
                continue

            asn, prefix = line.split("|", 1)

            try:
                ipaddress.ip_network(prefix)
            except Exception:
                continue

            prefixes.setdefault(asn, []).append(prefix)

    log(f"Loaded {len(prefixes)} ASN entries.")
    return prefixes


# =========================================================
# IP GENERATION
# =========================================================

def sample_ip_from_prefix(prefix):
    """
    Generate a random IP inside a CIDR.
    """

    network = ipaddress.ip_network(prefix, strict=False)

    if network.num_addresses <= 4:
        return None

    rand = random.randint(1, network.num_addresses - 2)

    return str(network.network_address + rand)


# =========================================================
# BASIC TCP PROBE
# =========================================================

def tcp_connect(ip, port):

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(CONNECT_TIMEOUT)

        result = sock.connect_ex((ip, port))

        if result == 0:
            return sock

        sock.close()
        return None

    except Exception:
        return None


# =========================================================
# BANNER PROBES
# =========================================================

def probe_ssh(ip):

    sock = tcp_connect(ip, 22)

    if not sock:
        return None

    try:
        banner = safe_recv(sock, 512).decode(errors="ignore").strip()

        return {
            "service": "ssh",
            "banner": banner
        }

    finally:
        sock.close()


def probe_smtp(ip):

    sock = tcp_connect(ip, 25)

    if not sock:
        return None

    try:
        banner = safe_recv(sock, 512).decode(errors="ignore").strip()

        return {
            "service": "smtp",
            "banner": banner
        }

    finally:
        sock.close()


def probe_http(ip, port=80):

    sock = tcp_connect(ip, port)

    if not sock:
        return None

    try:
        req = (
            f"HEAD / HTTP/1.1\r\n"
            f"Host: {ip}\r\n"
            f"Connection: close\r\n\r\n"
        )

        sock.send(req.encode())

        data = safe_recv(sock, 2048).decode(errors="ignore")

        return {
            "service": "http",
            "response": data
        }

    finally:
        sock.close()


def probe_tls(ip, port=443):

    try:
        ctx = ssl.create_default_context()

        sock = socket.create_connection(
            (ip, port),
            timeout=CONNECT_TIMEOUT
        )

        tls = ctx.wrap_socket(sock, server_hostname=ip)

        cert = tls.getpeercert()

        cipher = tls.cipher()

        tls.close()

        return {
            "service": "tls",
            "cipher": cipher,
            "cert": cert
        }

    except Exception:
        return None


# =========================================================
# ICMP TTL
# =========================================================

def estimate_ttl(ip):

    """
    Very lightweight TTL estimation using ping.
    Linux/macOS compatible.
    """

    try:

        proc = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True,
            text=True
        )

        output = proc.stdout.lower()

        if "ttl=" not in output:
            return None

        ttl = int(output.split("ttl=")[1].split()[0])

        return ttl

    except Exception:
        return None


# =========================================================
# PORT SCAN
# =========================================================

def scan_ports(ip):

    open_ports = []

    for port in COMMON_PORTS:

        sock = tcp_connect(ip, port)

        if sock:
            open_ports.append(port)
            sock.close()

    return open_ports


# =========================================================
# HOSTNAME
# =========================================================

def reverse_dns(ip):

    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host.lower()
    except Exception:
        return ""


# =========================================================
# OS DETECTION
# =========================================================

def detect_os(ttl, probes):

    scores = {
        "windows": 0,
        "linux": 0
    }

    # -----------------------------
    # TTL heuristic
    # -----------------------------

    if ttl:

        if ttl <= 64:
            scores["linux"] += 1

        elif ttl <= 128:
            scores["windows"] += 1

    # -----------------------------
    # SSH banners
    # -----------------------------

    ssh = probes.get("ssh")

    if ssh:

        banner = ssh.get("banner", "").lower()

        if "ubuntu" in banner:
            scores["linux"] += 3

        if "debian" in banner:
            scores["linux"] += 3

        if "openssh" in banner:
            scores["linux"] += 1

    # -----------------------------
    # HTTP headers
    # -----------------------------

    http = probes.get("http")

    if http:

        body = http.get("response", "").lower()

        if "iis" in body:
            scores["windows"] += 4

        if "apache" in body:
            scores["linux"] += 2

        if "nginx" in body:
            scores["linux"] += 2

    # -----------------------------
    # Conservative output
    # -----------------------------

    if scores["linux"] >= 3 and scores["linux"] > scores["windows"]:
        return "linux"

    if scores["windows"] >= 3 and scores["windows"] > scores["linux"]:
        return "windows"

    return "unknown"


# =========================================================
# MACHINE TYPE DETECTION
# =========================================================

def detect_machine_type(ports, hostname, probes):

    hostname = hostname.lower()

    # -----------------------------
    # CDN
    # -----------------------------

    if any(x in hostname for x in KNOWN_CDN_KEYWORDS):
        return "cdn"

    # -----------------------------
    # Router
    # -----------------------------

    if any(x in hostname for x in KNOWN_ROUTER_KEYWORDS):
        return "router"

    # -----------------------------
    # Mail
    # -----------------------------

    if 25 in ports or 587 in ports:
        return "mail_server"

    # -----------------------------
    # DNS
    # -----------------------------

    if 53 in ports:
        return "dns_server"

    # -----------------------------
    # Web
    # -----------------------------

    if 80 in ports or 443 in ports:
        return "web_server"

    # -----------------------------
    # Proxy
    # -----------------------------

    if 8080 in ports:
        return "proxy"

    return "unknown"


# =========================================================
# FILTERS
# =========================================================

def looks_like_honeypot(ports):

    """
    Very naive honeypot filter:
    too many uncommon ports open.
    """

    if len(ports) >= 10:
        return True

    return False


def is_valid_machine(machine):

    if not machine["ports"]:
        return False

    if machine["type_machine"] == "cdn":
        return False

    if looks_like_honeypot(machine["ports"]):
        return False

    return True


# =========================================================
# MACHINE BUILD
# =========================================================

def build_machine(ip, asn):

    hostname = reverse_dns(ip)

    ports = scan_ports(ip)

    if not ports:
        return None

    probes = {}

    if 22 in ports:
        probes["ssh"] = probe_ssh(ip)

    if 25 in ports:
        probes["smtp"] = probe_smtp(ip)

    if 80 in ports:
        probes["http"] = probe_http(ip, 80)

    if 443 in ports:
        probes["tls"] = probe_tls(ip, 443)

    ttl = estimate_ttl(ip)

    os_guess = detect_os(ttl, probes)

    machine_type = detect_machine_type(
        ports,
        hostname,
        probes
    )

    machine = {
        "id": ip,
        "ip": ip,
        "asn": asn,
        "provider": asn,
        "hostname": hostname,
        "country": "unknown",
        "ports": ports,
        "services_detected": list(probes.keys()),
        "os": os_guess,
        "type_machine": machine_type,
        "last_seen": now_ts(),
        "x": random.randint(-5000, 5000),
        "y": random.randint(-5000, 5000)
    }

    if not is_valid_machine(machine):
        return None

    return machine


# =========================================================
# DATABASE
# =========================================================

def load_database():

    if not os.path.exists(OUTPUT_FILE):

        return {
            "machines": [],
            "edges": [],
            "queue": []
        }

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_database(db):

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)


# =========================================================
# PROPAGATION
# =========================================================

def propagate_from_machine(machine):

    """
    Smart propagation:
    only propagate from valid machines.
    """

    ip = machine["ip"]

    try:

        a, b, c, d = ip.split(".")

        base = f"{a}.{b}.{c}"

        generated = []

        for _ in range(3):

            generated.append(
                f"{base}.{random.randint(1,254)}"
            )

        return generated

    except Exception:
        return []


# =========================================================
# MAIN ENGINE
# =========================================================

def run():

    prefixes = load_prefixes()

    db = load_database()

    existing = {
        m["ip"]: m
        for m in db["machines"]
    }

    q = db.get("queue", [])

    new_queue = []

    new_nodes = {}

    # -----------------------------------------------------
    # Initial seeding
    # -----------------------------------------------------

    if not q:

        for asn, plist in prefixes.items():

            for prefix in plist[:3]:

                for _ in range(2):

                    ip = sample_ip_from_prefix(prefix)

                    if ip:
                        q.append({
                            "ip": ip,
                            "asn": asn
                        })

    random.shuffle(q)

    # -----------------------------------------------------
    # Crawl
    # -----------------------------------------------------

    count = 0

    while q and count < MAX_NEW_PER_RUN:

        item = q.pop(0)

        ip = item["ip"]
        asn = item["asn"]

        if ip in existing:
            continue

        if is_private_ip(ip):
            continue

        log(f"Scanning {ip}")

        try:

            machine = build_machine(ip, asn)

            if not machine:
                continue

            new_nodes[ip] = machine

            count += 1

            log(
                f"[+] {ip} "
                f"{machine['type_machine']} "
                f"{machine['os']}"
            )

            # ---------------------------------------------
            # Propagation
            # ---------------------------------------------

            for new_ip in propagate_from_machine(machine):

                if new_ip not in existing:

                    new_queue.append({
                        "ip": new_ip,
                        "asn": asn
                    })

        except KeyboardInterrupt:
            break

        except Exception as e:
            log(f"Error: {e}")

    # -----------------------------------------------------
    # Merge
    # -----------------------------------------------------

    merged = list(existing.values())

    for m in new_nodes.values():
        merged.append(m)

    db["machines"] = merged
    db["queue"] = new_queue

    # -----------------------------------------------------
    # Edges
    # -----------------------------------------------------

    edges = []

    for m in merged:
        edges.append([m["asn"], m["ip"]])

    db["edges"] = edges

    save_database(db)

    log(f"Done.")
    log(f"New machines: {count}")
    log(f"Queue: {len(new_queue)}")


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":
    run()
