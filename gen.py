"""
WebMap Crawler — FINAL PRO VERSION + NODE CENTRAL
100 nouveaux nœuds par session
JSON illimité
Frontier persistante
Node central : https://webmap.ct.ws
"""

import threading, queue, time, random, logging, requests, json, os
from urllib.parse import urljoin
from bs4 import BeautifulSoup

GRID_SIZE = 100000
NEW_NODES_PER_RUN = 100
THREADS = 6
REQUEST_TIMEOUT = 8

OUTPUT_JSON = "webmap.json"
FRONTIER_JSON = "frontier.json"

# Node central
CENTRAL_URL = "https://webmap.ct.ws"
CENTRAL_FAVICON = "https://webmap.ct.ws/assets/favicon.png"
CENTRAL_X = GRID_SIZE // 2
CENTRAL_Y = GRID_SIZE // 2

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

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("WebMapCrawler")

nodes = {}
edges = []
visited = set()
frontier = []

nodes_lock = threading.Lock()
edges_lock = threading.Lock()
visited_lock = threading.Lock()
counter_lock = threading.Lock()
frontier_lock = threading.Lock()

task_queue = queue.Queue()

new_nodes_count = 0
stop_flag = False

# ============================================================
# LOAD JSON + FRONTIER
# ============================================================

def load_existing():
    global nodes, edges, visited, frontier

    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        for n in data.get("nodes", []):
            nodes[n["url"]] = n
        for e in data.get("edges", []):
            edges.append((e[0], e[1]))
        visited = set(nodes.keys())
        log.info(f"JSON chargé : {len(nodes)} nodes")

    if os.path.exists(FRONTIER_JSON):
        with open(FRONTIER_JSON, "r", encoding="utf-8") as f:
            frontier = json.load(f)
        log.info(f"Frontier chargée : {len(frontier)} URLs")

# ============================================================
# SAVE JSON + FRONTIER
# ============================================================

def save_all():
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"nodes": list(nodes.values()), "edges": list(edges)}, f, indent=2)

    with open(FRONTIER_JSON, "w", encoding="utf-8") as f:
        json.dump(frontier, f, indent=2)

    log.info(f"[SAVE] JSON + Frontier sauvegardés ({len(nodes)} nodes)")

# ============================================================
# STOP
# ============================================================

def stop_all():
    global stop_flag
    stop_flag = True
    log.info(">>> STOP FLAG — session terminée")

    while not task_queue.empty():
        try:
            task_queue.get_nowait()
            task_queue.task_done()
        except:
            break

# ============================================================
# HELPERS
# ============================================================

def safe_get(url):
    try:
        return requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    except:
        return None

def extract_links(url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(url, a["href"]).split("#")[0]
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

# ============================================================
# ADD NODE
# ============================================================

def add_node(url):
    global new_nodes_count, stop_flag

    if stop_flag:
        return False
    if url in nodes:
        return False

    with counter_lock:
        if new_nodes_count >= NEW_NODES_PER_RUN:
            stop_all()
            return False

    status = check_status(url)
    favicon = check_favicon(url)
    x, y = get_free_coordinates()

    node = {"url": url, "favicon": favicon, "status": status, "x": x, "y": y}

    with nodes_lock:
        nodes[url] = node

    with counter_lock:
        new_nodes_count += 1
        log.info(f"[NODE] {url} | new={new_nodes_count}")

        if new_nodes_count >= NEW_NODES_PER_RUN:
            stop_all()

    return True

# ============================================================
# CENTRAL NODE HANDLING
# ============================================================

def ensure_central_node():
    """Ajoute https://webmap.ct.ws au centre si absent."""
    if CENTRAL_URL not in nodes:
        log.info("Ajout du node central WebMap.ct.ws")

        nodes[CENTRAL_URL] = {
            "url": CENTRAL_URL,
            "favicon": CENTRAL_FAVICON,
            "status": 1,
            "x": CENTRAL_X,
            "y": CENTRAL_Y
        }

    # Connecter TOUS les nodes au central
    for url in nodes:
        if url != CENTRAL_URL:
            edges.append((CENTRAL_URL, url))

# ============================================================
# CRAWL
# ============================================================

def crawl_site(url):
    if stop_flag:
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
        if stop_flag:
            break

        created = add_node(link)

        with edges_lock:
            edges.append((url, link))
            edges.append((CENTRAL_URL, link))  # connexion au node central

        if created:
            task_queue.put(link)
        else:
            with frontier_lock:
                if link not in frontier:
                    frontier.append(link)

# ============================================================
# WORKER
# ============================================================

def worker():
    while True:
        if stop_flag:
            return
        try:
            url = task_queue.get(timeout=0.5)
        except queue.Empty:
            return
        crawl_site(url)
        task_queue.task_done()

# ============================================================
# MAIN
# ============================================================

def main():
    global stop_flag

    log.info("=== WebMap Crawler — FINAL PRO MODE + NODE CENTRAL ===")

    load_existing()
    ensure_central_node()

    # Seeds
    for s in SEED_SITES:
        task_queue.put(s)

    # Frontier
    with frontier_lock:
        for url in frontier[:200]:
            task_queue.put(url)

    # Ancien nodes
    for url in list(nodes.keys())[:50]:
        task_queue.put(url)

    # Threads
    for _ in range(THREADS):
        threading.Thread(target=worker, daemon=True).start()

    idle = 0
    while True:
        if stop_flag:
            break

        if task_queue.empty():
            idle += 1
        else:
            idle = 0

        if idle > 40:
            log.info("Plus de travail → arrêt session")
            break

        time.sleep(0.1)

    stop_all()
    ensure_central_node()
    save_all()
    log.info(f"Session terminée — {new_nodes_count} nouveaux nœuds ajoutés")

if __name__ == "__main__":
    main()
