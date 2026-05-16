"""
WebMap Crawler — FINAL PRO VERSION + NODE CENTRAL
100 nouveaux nœuds par session
JSON illimité
Frontier persistante
Node central : https://webmap.ct.ws
"""

import threading, queue, time, random, logging, requests, json, os
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

GRID_SIZE = 1000
NEW_NODES_PER_RUN = 500
THREADS = 8
REQUEST_TIMEOUT = 8

OUTPUT_JSON = "webmap.json"
FRONTIER_JSON = "frontier.json"

# Node central
CENTRAL_URL = "https://webmap.ct.ws"
CENTRAL_FAVICON = "https://webmap.ct.ws/assets/favicon.png"
CENTRAL_X = GRID_SIZE // 2
CENTRAL_Y = GRID_SIZE // 2

SEED_SITES = [

    # Social / communautés supplémentaires
    "https://reddit.com",
    "https://webmap.ct.ws",
    "https://wikipedia.org",
    "https://archive.org",
    "https://web.archive.org",
    "https://openstreetmap.org",
    "https://matrix.org",
    "https://mastodon.social",
    "https://proton.me",
    "https://startpage.com",
    "https://github.com",
    "https://discord.com",
    "https://telegram.org",
    "https://signal.org",
    "https://irccloud.com",
    "https://libera.chat",
    "https://slashdot.org",
    "https://tildes.net",
    "https://discourse.org",
    "https://nodebb.org",
    "https://invisioncommunity.com",

    # Search / moteurs
    "https://duckduckgo.com",
    "https://bing.com",
    "https://google.com",
    "https://yandex.com",
    "https://yacy.net",
    "https://mojeek.com",
    "https://brave search.com",
    "https://searchcode.com",

    # OSINT avancé
    "https://hunter.io",
    "https://phonebook.cz",
    "https://crt.sh",
    "https://wigle.net",
    "https://urlscan.io",
    "https://dnsdumpster.com",
    "https://securitytrails.com",
    "https://onyphe.io",
    "https://greynoise.io",
    "https://zoomeye.org",
    "https://fullhunt.io",
    "https://netlas.io",
    "https://fofa.info",

    # Malware / sandbox
    "https://hybrid-analysis.com",
    "https://any.run",
    "https://tria.ge",
    "https://vx-underground.org",
    "https://malshare.com",
    "https://urlhaus.abuse.ch",
    "https://bazaar.abuse.ch",
    "https://malpedia.caad.fkie.fraunhofer.de",

    # Reverse / low-level
    "https://godbolt.org",
    "https://osdev.org",
    "https://lowlevel.eu",
    "https://fabiensanglard.net",
    "https://ref.x86asm.net",
    "https://felixcloutier.com/x86",
    "https://kernel.org",
    "https://uops.info",

    # FPGA / embedded
    "https://zephyrproject.org",
    "https://platformio.org",
    "https://riot-os.org",
    "https://contiki-ng.org",
    "https://beagleboard.org",
    "https://pine64.org",
    "https://siemens.com",
    "https://nxp.com",
    "https://microchip.com",

    # Clouds
    "https://aws.amazon.com",
    "https://cloud.google.com",
    "https://azure.microsoft.com",
    "https://cloudflare.com",
    "https://digitalocean.com",
    "https://render.com",
    "https://fly.io",
    "https://railway.app",
    "https://vercel.com",
    "https://netlify.com",

    # Containers / virtualization
    "https://lxc.org",
    "https://linuxcontainers.org",
    "https://podman.io",
    "https://containerd.io",
    "https://cri-o.io",
    "https://k3s.io",
    "https://k0sproject.io",
    "https://openstack.org",
    "https://xenproject.org",
    "https://qemu.org",

    # Monitoring
    "https://zabbix.com",
    "https://nagios.org",
    "https://netdata.cloud",
    "https://checkmk.com",
    "https://uptimerobot.com",

    # Databases supplémentaires
    "https://postgresql.org",
    "https://mongodb.com",
    "https://redis.io",
    "https://sqlite.org",
    "https://supabase.com",
    "https://planetscale.com",
    "https://cockroachlabs.com",
    "https://surrealdb.com",
    "https://duckdb.org",

    # APIs / backend
    "https://fastapi.tiangolo.com",
    "https://nestjs.com",
    "https://expressjs.com",
    "https://flask.palletsprojects.com",
    "https://laravel.com",
    "https://symfony.com",
    "https://spring.io",
    "https://ktor.io",
    "https://actix.rs",

    # Frontend
    "https://astro.build",
    "https://solidjs.com",
    "https://qwik.builder.io",
    "https://preactjs.com",
    "https://threejs.org",
    "https://babylonjs.com",
    "https://pixijs.com",
    "https://vitejs.dev",

    # Mobile
    "https://flutter.dev",
    "https://reactnative.dev",
    "https://ionicframework.com",
    "https://expo.dev",
    "https://capacitorjs.com",

    # AI / ML
    "https://huggingface.co",
    "https://openai.com",
    "https://anthropic.com",
    "https://deepmind.google",
    "https://together.ai",
    "https://vllm.ai",
    "https://llamaindex.ai",
    "https://modal.com",
    "https://runpod.io",
    "https://banana.dev",
    "https://pytorch.org",
    "https://tensorflow.org",
    "https://jax.readthedocs.io",
    "https://onnx.ai",
    "https://keras.io",

    # Data science
    "https://pandas.pydata.org",
    "https://numpy.org",
    "https://scipy.org",
    "https://matplotlib.org",
    "https://plotly.com",
    "https://polars.rs",

    # Crypto / blockchain
    "https://ethereum.org",
    "https://solana.com",
    "https://bitcoin.org",
    "https://monero.org",
    "https://chain.link",
    "https://opensea.io",
    "https://etherscan.io",

    # Pentest / sécurité
    "https://burpsuite.com",
    "https://wireshark.org",
    "https://nmap.org",
    "https://aircrack-ng.org",
    "https://hashcat.net",
    "https://johntheripper.com",
    "https://gobuster.com",
    "https://ffuf.me",
    "https://sqlmap.org",
    "https://impacket.org",

    # Téléchargements / packages
    "https://npmjs.com",
    "https://pypi.org",
    "https://rubygems.org",
    "https://crates.io",
    "https://packagist.org",
    "https://search.maven.org",
    "https://anaconda.org",

    # Web scraping
    "https://scrapy.org",
    "https://playwright.dev",
    "https://selenium.dev",
    "https://beautiful-soup-4.readthedocs.io",
    "https://puppeteer.dev",

    # Cartographie / SIG
    "https://qgis.org",
    "https://cesium.com",
    "https://leafletjs.com",
    "https://mapbox.com",

    # Robotique
    "https://ros.org",
    "https://gazebosim.org",
    "https://openrobotics.org",

    # Satellites / météo
    "https://weather.com",
    "https://windy.com",
    "https://sat24.com",
    "https://earth.nullschool.net",

    # Streaming tech
    "https://obsproject.com",
    "https://ffmpeg.org",
    "https://vlc.org",

    # Compression / formats
    "https://7-zip.org",
    "https://rarlab.com",
    "https://zstd.net",

    # Documentation / specs
    "https://ietf.org",
    "https://rfc-editor.org",
    "https://ecma-international.org",
    "https://unicode.org",
    "https://iso.org",

    # Sysadmin
    "https://fail2ban.org",
    "https://cockpit-project.org",
    "https://webmin.com",
    "https://phpmyadmin.net",

    # CMS / web
    "https://wordpress.org",
    "https://drupal.org",
    "https://joomla.org",
    "https://ghost.org",

    # Automation
    "https://n8n.io",
    "https://zapier.com",
    "https://ifttt.com",

    # Homelab
    "https://homelabos.com",
    "https://selfh.st",
    "https://awesome-selfhosted.net",

    # Vidéo / GPU / rendering
    "https://opencv.org",
    "https://open3d.org",
    "https://opencl.org",
    "https://cuda.zone",

    # Physique / maths
    "https://wolfram.com",
    "https://desmos.com",
    "https://overleaf.com",

    # Journaux / actu internationale
    "https://reuters.com",
    "https://apnews.com",
    "https://bbc.com",
    "https://aljazeera.com",

    # DNS / réseau
    "https://cloudns.net",
    "https://freedns.afraid.org",
    "https://noip.com",
    "https://dynu.com",

    # Email / SMTP
    "https://mailcow.email",
    "https://roundcube.net",
    "https://rspamd.com",

    # Forums gaming / modding
    "https://nexusmods.com",
    "https://gamebanana.com",
    "https://fearlessrevolution.com",

    # Benchmarks / hardware
    "https://cpubenchmark.net",
    "https://gpucheck.com",
    "https://techpowerup.com",

    # Android / mobile hacking
    "https://apkmirror.com",
    "https://f-droid.org",
    "https://lineageos.org",
    "https://grapheneos.org",
    "https://calyxos.org",

    # Darknet / privacy
    "https://onionshare.org",
    "https://i2p.net",
    "https://geti2p.net",

    # Knowledge / archive
    "https://archive.today",
    "https://memory-alpha.fandom.com",
    "https://internetlivestats.com",

    # Misc dev
    "https://regex101.com",
    "https://jsonformatter.org",
    "https://httpbin.org",
    "https://reqbin.com",
    "https://ipinfo.io",
    "https://icanhazip.com",
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
edges_set = set()
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
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                log.warning(f"{OUTPUT_JSON} est vide, nouvelle structure créée")
                data = {}
            else:
                data = json.loads(content)
        except json.JSONDecodeError as e:
            log.warning(f"Impossible de parser {OUTPUT_JSON} : {e}. Contenu ignoré.")
            data = {}
        except Exception as e:
            log.warning(f"Erreur de lecture {OUTPUT_JSON} : {e}. Contenu ignoré.")
            data = {}

        for n in data.get("nodes", []):
            url = canonical_url(n["url"])
            if url in nodes:
                continue
            n["url"] = url
            if "added_at" not in n:
                n["added_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            if "added_date" not in n:
                n["added_date"] = n["added_at"][:10]
            if "added_time" not in n:
                n["added_time"] = n["added_at"][11:16]
            if "added_day" not in n:
                n["added_day"] = datetime.utcnow().strftime("%A")
            nodes[url] = n
        for e in data.get("edges", []):
            src = canonical_url(e[0])
            dst = canonical_url(e[1])
            if src and dst and (src, dst) not in edges_set:
                edges.append((src, dst))
                edges_set.add((src, dst))
        # Do not mark existing saved nodes as already visited in this session.
        # Otherwise, old nodes never get crawled again after load.
        log.info(f"JSON chargé : {len(nodes)} nodes")

    if os.path.exists(FRONTIER_JSON):
        try:
            with open(FRONTIER_JSON, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                log.warning(f"{FRONTIER_JSON} est vide, nouvelle frontier créée")
                frontier = []
            else:
                frontier = json.loads(content)
        except json.JSONDecodeError as e:
            log.warning(f"Impossible de parser {FRONTIER_JSON} : {e}. Contenu ignoré.")
            frontier = []
        except Exception as e:
            log.warning(f"Erreur de lecture {FRONTIER_JSON} : {e}. Contenu ignoré.")
            frontier = []
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

def root_host(host):
    if not host:
        return ""
    host = host.lower().strip('.')
    if host == "ct.ws":
        return "webmap.ct.ws"
    if host.startswith("www."):
        host = host[4:]

    aliases = {
        "twitter.com": "x.com",
        "x.com": "x.com",
        "fb.com": "facebook.com",
        "facebook.com": "facebook.com",
        "m.facebook.com": "facebook.com",
    }
    if host in aliases:
        return aliases[host]

    parts = host.split('.')
    if len(parts) <= 2:
        return host

    suffixes = {
        "co.uk", "org.uk", "gov.uk", "ac.uk", "sch.uk",
        "net.au", "com.au", "org.au", "gov.au", "edu.au",
        "co.nz", "gov.nz", "ac.nz", "co.jp", "ne.jp",
        "or.jp", "go.jp", "ac.jp", "co.za", "gov.za"
    }

    for suffix in suffixes:
        if host.endswith('.' + suffix):
            parts = host[:-len(suffix) - 1].split('.')
            return '.'.join(parts[-1:] + suffix.split('.')) if parts else suffix

    return '.'.join(parts[-2:])


def canonical_url(url):
    if not url or not isinstance(url, str):
        return url
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    # Always canonicalize storage to HTTPS to avoid protocol duplicates
    scheme = "https"
    host = root_host(parsed.hostname or parsed.path)
    if not host:
        return url
    normalized = f"{scheme}://{host}"
    return normalized


def add_edge(src, dst):
    src = canonical_url(src)
    dst = canonical_url(dst)
    if not src or not dst:
        return False
    with edges_lock:
        if (src, dst) in edges_set:
            return False
        edges.append((src, dst))
        edges_set.add((src, dst))
    return True


def safe_get(url):
    # Try HTTPS first (canonical storage), then fall back to HTTP if HTTPS fails
    url = canonical_url(url)
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        if r is not None and r.status_code < 500:
            return r
    except Exception:
        pass

    # fallback to http
    try:
        if url.startswith("https://"):
            alt = "http://" + url[len("https://"):]
        else:
            alt = url.replace("https://", "http://")
        r2 = requests.get(alt, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        return r2
    except Exception:
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
        url = canonical_url(url)
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
        with nodes_lock:
            if all(n["x"] != x or n["y"] != y for n in nodes.values()):
                return x, y

# ============================================================
# ADD NODE
# ============================================================

def add_node(url):
    global new_nodes_count, stop_flag

    url = canonical_url(url)
    if stop_flag or not url:
        return False
    with nodes_lock:
        if url in nodes:
            return False

    with counter_lock:
        if new_nodes_count >= NEW_NODES_PER_RUN:
            stop_all()
            return False

    status = check_status(url)
    favicon = check_favicon(url)
    x, y = get_free_coordinates()
    now = datetime.now(timezone.utc)

    node = {
        "url": url,
        "favicon": favicon,
        "status": status,
        "x": x,
        "y": y,
        "added_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "added_date": now.strftime("%Y-%m-%d"),
        "added_time": now.strftime("%H:%M"),
        "added_day": now.strftime("%A")
    }

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
        now = datetime.now(timezone.utc)

        nodes[CENTRAL_URL] = {
            "url": CENTRAL_URL,
            "favicon": CENTRAL_FAVICON,
            "status": 1,
            "x": CENTRAL_X,
            "y": CENTRAL_Y,
            "added_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "added_date": now.strftime("%Y-%m-%d"),
            "added_time": now.strftime("%H:%M"),
            "added_day": now.strftime("%A")
        }

    # Connecter TOUS les nodes au central
    for url in nodes:
        if url != CENTRAL_URL:
            add_edge(CENTRAL_URL, url)

# ============================================================
# CRAWL
# ============================================================

def crawl_site(url):
    if stop_flag:
        return

    url = canonical_url(url)
    if not url:
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

        link = canonical_url(link)
        if not link:
            continue

        created = add_node(link)

        add_edge(url, link)
        add_edge(CENTRAL_URL, link)  # connexion au node central

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
        task_queue.put(canonical_url(s))

    # Frontier
    with frontier_lock:
        for url in frontier[:1000]:
            task_queue.put(canonical_url(url))

    # Ancien nodes
    for url in list(nodes.keys())[:200]:
        task_queue.put(canonical_url(url))

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
