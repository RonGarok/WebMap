"""
WebMap Crawler — Version GitHub Actions
Génère webmap.json localement, GitHub Actions fera commit + push.
Aucune requête vers InfinityFree.
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

# ==========================
# CONFIG
# ==========================

GRID_SIZE = 1000
MAX_NODES = 500
THREADS = 1
REQUEST_TIMEOUT = 10

OUTPUT_JSON = "webmap.json"

SEED_SITES = [
    "https://wikipedia.org",
    "https://reddit.com",
    "https://github.com",
    "https://stackoverflow.com",
    "https://python.org",
    "https://mozilla.org",
    "https://gnu.org",
    "https://linux.org",
    "https://ubuntu.com",
    "https://debian.org",
    "https://archlinux.org",
    "https://apple.com",
    "https://google.com",
    "https://bing.com",
    "https://duckduckgo.com",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
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

nodes_lock = threading.Lock()
edges_lock = threading.Lock()
visited_lock = threading.Lock()

nodes = {}
edges = []
visited = set()

task_queue = queue.Queue()

# ==========================
# HELPERS
# ==========================

def get_base_domain(url):
    host = urlparse(url).netloc.lower()
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def get_node_count():
    with nodes_lock:
        return len(nodes)


def node_exists(url):
    with nodes_lock:
        return url in nodes


def coordinates_taken(x, y):
    with nodes_lock:
        for n in nodes.values():
            if n["x"] == x and n["y"] == y:
                return True
    return False


def get_free_coordinates():
    while True:
        x = random.randint(0, GRID_SIZE)
        y = random.randint(0, GRID_SIZE)
        if not coordinates_taken(x, y):
            return x, y


def safe_get(url):
    try:
        return requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    except:
        return None


def extract_links(url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    base_domain = get_base_domain(url)

    for a in soup.find_all("a", href=True):
        full = urljoin(url, a["href"])
        full = full.split("#")[0]

        if not full.startswith("http"):
            continue

        target_domain = get_base_domain(full)

        if target_domain == base_domain:
            continue

        links.add(full)

    return list(links)


def check_favicon(url):
    try:
        ico = url.rstrip("/") + "/favicon.ico"
        r = requests.get(ico, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        if r.status_code == 200:
            return ico
        return "default"
    except:
        return "default"


def check_status(url):
    r = safe_get(url)
    return 1 if r and r.status_code == 200 else 0


# ==========================
# CRAWLER CORE
# ==========================

def add_node(url):
    if get_node_count() >= MAX_NODES:
        return False

    if node_exists(url):
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

    log.info(f"[NODE] {url} | status={status} | favicon={favicon} | ({x},{y})")

    return True


def crawl_site(url):
    with visited_lock:
        if url in visited:
            return
        visited.add(url)

    if get_node_count() >= MAX_NODES:
        return

    r = safe_get(url)
    if not r or not r.text:
        return

    links = extract_links(url, r.text)

    for link in links:
        if get_node_count() >= MAX_NODES:
            break

        created = add_node(link)

        with edges_lock:
            edges.append((url, link))

        if created:
            task_queue.put(link)


def worker():
    while True:
        try:
            url = task_queue.get(timeout=3)
        except queue.Empty:
            return

        crawl_site(url)
        task_queue.task_done()


# ==========================
# EXPORT JSON
# ==========================

def export_json():
    data = {
        "nodes": list(nodes.values()),
        "edges": [[a, b] for a, b in edges]
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log.info(f"[JSON] Exporté dans {OUTPUT_JSON}")


# ==========================
# MAIN
# ==========================

def main():
    log.info("Démarrage du crawler WebMap (GitHub Actions)...")

    # Ajout des seeds
    for url in SEED_SITES:
        if add_node(url):
            task_queue.put(url)

    # Threads
    for _ in range(THREADS):
        threading.Thread(target=worker, daemon=True).start()

    task_queue.join()

    log.info(f"Terminé. Nœuds finaux: {get_node_count()}/{MAX_NODES}")

    export_json()


if __name__ == "__main__":
    main()
