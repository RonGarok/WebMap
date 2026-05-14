"""
WebMap Crawler — Mode continu
- Charge webmap.json si présent
- Ajoute jusqu'à +100 nouveaux nodes
- Sauvegarde et s'arrête
"""

import threading
import queue
import time
import random
import logging
import requests
import json
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import os

# ==========================
# CONFIG
# ==========================

GRID_SIZE = 100000
NEW_NODES_PER_RUN = 100
THREADS = 4
REQUEST_TIMEOUT = 8

OUTPUT_JSON = "webmap.json"

SEED_SITES = [
    "https://wikipedia.org",
    "https://reddit.com",
    "https://github.com",
    "https://stackoverflow.com",
    "https://python.org",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (WebMapCrawler)",
    "Accept": "*/*",
    "Connection": "close"
}

# ==========================
# LOGGING
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("WebMapCrawler")

# ==========================
# DATA STRUCTURES
# ==========================

nodes = {}          # url -> node
edges = []          # (from, to)
visited = set()     # urls déjà crawlées

nodes_lock = threading.Lock()
edges_lock = threading.Lock()
visited_lock = threading.Lock()

task_queue = queue.Queue()

new_nodes_count = 0

# ==========================
# LOAD EXISTING JSON
# ==========================

def load_existing():
    global nodes, edges, visited

    if not os.path.exists(OUTPUT_JSON):
        log.info("Aucun JSON existant → utilisation des seeds.")
        return

    try:
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        for n in data.get("nodes", []):
            nodes[n["url"]] = n

        for e in data.get("edges", []):
            edges.append((e[0], e[1]))

        visited = set(nodes.keys())

        log.info(f"JSON existant chargé : {len(nodes)} nodes, {len(edges)} edges")

    except Exception as e:
        log.error(f"Erreur chargement JSON : {e}")

# ==========================
# HELPERS
# ==========================

def get_base_domain(url):
    host = urlparse(url).netloc.lower()
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def safe_get(url):
    try:
        return requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    except:
        return None


def extract_links(url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        full = urljoin(url, a["href"])
        full = full.split("#")[0]
        if full.startswith("http"):
            links.add(full)

    return list(links)


def check_favicon(url):
    try:
        ico = url.rstrip("/") + "/favicon.ico"
        r = requests.get(ico, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        return ico if r.status_code == 200 else "default"
    except:
        return "default"


def check_status(url):
    r = safe_get(url)
    return 1 if r and r.status_code == 200 else 0


def get_free_coordinates():
    while True:
        x = random.randint(0, GRID_SIZE)
        y = random.randint(0, GRID_SIZE)
        if all(n["x"] != x or n["y"] != y for n in nodes.values()):
            return x, y

# ==========================
# ADD NODE
# ==========================

def add_node(url):
    global new_nodes_count

    if url in nodes:
        return False

    if new_nodes_count >= NEW_NODES_PER_RUN:
        return False

    status = check_status(url)
    favicon = check_favicon(url)
    x, y = get_free_coordinates()

    node = {
        "url": url,
        "favicon": favicon,
        "status": status,
        "x": x,
        "y": y
    }

    with nodes_lock:
        nodes[url] = node

    new_nodes_count += 1

    log.info(f"[NODE] {url} | status={status} | ({x},{y})")

    return True

# ==========================
# CRAWL
# ==========================

def crawl_site(url):
    global new_nodes_count

    if new_nodes_count >= NEW_NODES_PER_RUN:
        return

    with visited_lock:
        if url in visited:
            return
        visited.add(url)

    r = safe_get(url)
    if not r or not r.text:
        return

    links = extract_links(url, r.text)

    for link in links:
        if new_nodes_count >= NEW_NODES_PER_RUN:
            break

        created = add_node(link)

        with edges_lock:
            edges.append((url, link))

        if created:
            task_queue.put(link)


def worker():
    while True:
        if new_nodes_count >= NEW_NODES_PER_RUN:
            return

        try:
            url = task_queue.get(timeout=1)
        except queue.Empty:
            return

        crawl_site(url)
        task_queue.task_done()

# ==========================
# SAVE JSON
# ==========================

def save_json():
    data = {
        "nodes": list(nodes.values()),
        "edges": list(edges)
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log.info(f"[JSON] Sauvegardé — total {len(nodes)} nodes")

# ==========================
# MAIN
# ==========================

def main():
    load_existing()

    # Si aucun node → utiliser les seeds
    if len(nodes) == 0:
        for s in SEED_SITES:
            add_node(s)
            task_queue.put(s)
    else:
        # Repartir des nodes existants
        for url in list(nodes.keys())[:20]:
            task_queue.put(url)

    # Threads
    for _ in range(THREADS):
        threading.Thread(target=worker, daemon=True).start()

    # Attendre fin
    while new_nodes_count < NEW_NODES_PER_RUN and not task_queue.empty():
        time.sleep(0.1)

    save_json()
    log.info("Run terminé.")

if __name__ == "__main__":
    main()
