"""
WebMap Crawler — RUN 100 NODES MAX
"""

import threading, queue, time, random, logging, requests, json, os
from urllib.parse import urljoin
from bs4 import BeautifulSoup

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

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("WebMapCrawler")

nodes = {}
edges = []
visited = set()

nodes_lock = threading.Lock()
edges_lock = threading.Lock()
visited_lock = threading.Lock()
counter_lock = threading.Lock()

task_queue = queue.Queue()

new_nodes_count = 0
stop_flag = False


def load_existing():
    global nodes, edges, visited
    if not os.path.exists(OUTPUT_JSON):
        log.info("Aucun JSON existant → seeds.")
        return
    try:
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        for n in data.get("nodes", []):
            nodes[n["url"]] = n
        for e in data.get("edges", []):
            edges.append((e[0], e[1]))
        visited = set(nodes.keys())
        log.info(f"JSON chargé : {len(nodes)} nodes, {len(edges)} edges")
    except Exception as e:
        log.error(f"Erreur JSON : {e}")


def stop_all():
    global stop_flag
    stop_flag = True
    log.info(">>> STOP FLAG ACTIVÉ — arrêt du crawler")
    while not task_queue.empty():
        try:
            task_queue.get_nowait()
            task_queue.task_done()
        except:
            break


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


def add_node(url):
    global new_nodes_count
    if stop_flag or url in nodes:
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
        current = new_nodes_count

    log.info(f"[NODE] {url} | status={status} | ({x},{y}) | new_nodes={current}")

    if current >= NEW_NODES_PER_RUN:
        stop_all()

    return True


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
        if created and not stop_flag:
            task_queue.put(link)


def worker():
    while True:
        if stop_flag:
            return
        try:
            url = task_queue.get(timeout=0.5)
        except queue.Empty:
            return
        if stop_flag:
            task_queue.task_done()
            return
        crawl_site(url)
        task_queue.task_done()
        if stop_flag:
            return


def save_json():
    data = {"nodes": list(nodes.values()), "edges": list(edges)}
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"[JSON] Sauvegardé — total {len(nodes)} nodes")


def main():
    global stop_flag
    log.info("=== WebMap Crawler — RUN 100 NODES MAX ===")

    load_existing()

    if len(nodes) == 0:
        log.info("Aucun node → seeds")
        for s in SEED_SITES:
            add_node(s)
            task_queue.put(s)
    else:
        log.info("Reprise depuis JSON existant")
        for url in list(nodes.keys())[:20]:
            task_queue.put(url)

    for _ in range(THREADS):
        threading.Thread(target=worker, daemon=True).start()

    idle_ticks = 0
    while True:
        if stop_flag:
            break
        if task_queue.empty():
            idle_ticks += 1
        else:
            idle_ticks = 0
        if idle_ticks > 20:  # ~2 secondes sans travail
            log.info("Plus de travail → arrêt")
            break
        time.sleep(0.1)

    stop_all()
    save_json()
    log.info(f"Run terminé. Nouveaux nœuds ajoutés : {new_nodes_count}")


if __name__ == "__main__":
    main()
