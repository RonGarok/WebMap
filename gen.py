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

GRID_SIZE = 10000000
NEW_NODES_PER_RUN = 5000
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
    # Forums / communautés
    "https://4chan.org",
    "https://8kun.top",
    "https://quora.com",
    "https://stackexchange.com",
    "https://askubuntu.com",
    "https://unix.stackexchange.com",
    "https://superuser.com",
    "https://serverfault.com",
    "https://mathoverflow.net",
    "https://forum.xda-developers.com",
    "https://linuxquestions.org",
    "https://ubuntuforums.org",
    "https://archlinuxbbs.org",
    "https://forums.debian.net",
    "https://forums.freebsd.org",
    "https://forums.gentoo.org",

    # Dev / code
    "https://gitlab.com",
    "https://bitbucket.org",
    "https://sourceforge.net",
    "https://codeberg.org",
    "https://gitea.io",
    "https://gist.github.com",
    "https://git-scm.com",
    "https://cmake.org",
    "https://mesonbuild.com",
    "https://bazel.build",
    "https://gradle.org",
    "https://maven.org",
    "https://ant.apache.org",
    "https://jenkins.io",
    "https://circleci.com",
    "https://travis-ci.com",
    "https://appveyor.com",
    "https://sonarqube.org",

    # Langages
    "https://rust-lang.org",
    "https://ziglang.org",
    "https://nim-lang.org",
    "https://crystal-lang.org",
    "https://elixir-lang.org",
    "https://erlang.org",
    "https://haskell.org",
    "https://ocaml.org",
    "https://racket-lang.org",
    "https://julialang.org",
    "https://dart.dev",
    "https://kotlinlang.org",
    "https://scala-lang.org",
    "https://clojure.org",
    "https://fortran-lang.org",

    # Docs / références
    "https://developer.mozilla.org",
    "https://learn.microsoft.com",
    "https://developers.google.com",
    "https://developer.android.com",
    "https://developer.apple.com",
    "https://docs.python.org",
    "https://docs.rs",
    "https://readthedocs.io",
    "https://devdocs.io",
    "https://cplusplus.com",
    "https://cppreference.com",
    "https://man7.org",
    "https://tldp.org",

    # Linux / systèmes
    "https://gentoo.org",
    "https://alpinelinux.org",
    "https://linuxfromscratch.org",
    "https://openwrt.org",
    "https://proxmox.com",
    "https://freedesktop.org",
    "https://systemd.io",
    "https://busybox.net",
    "https://yoctoproject.org",
    "https://slackware.com",
    "https://voidlinux.org",
    "https://kali.org",
    "https://parrotsec.org",
    "https://tails.net",

    # Cyber
    "https://cve.mitre.org",
    "https://nvd.nist.gov",
    "https://exploit-db.com",
    "https://packetstormsecurity.com",
    "https://owasp.org",
    "https://hackthebox.com",
    "https://tryhackme.com",
    "https://bleepingcomputer.com",
    "https://krebsonsecurity.com",
    "https://cisa.gov",
    "https://virustotal.com",
    "https://abuse.ch",
    "https://malwarebytes.com",
    "https://metasploit.com",
    "https://snort.org",
    "https://suricata.io",
    "https://offsec.com",
    "https://shodan.io",
    "https://censys.io",

    # Reverse engineering
    "https://ghidra-sre.org",
    "https://hex-rays.com",
    "https://ida-pro.net",
    "https://x64dbg.com",
    "https://radare.org",
    "https://binary.ninja",

    # IA
    "https://mistral.ai",
    "https://perplexity.ai",
    "https://ollama.com",
    "https://replicate.com",
    "https://cohere.com",
    "https://stability.ai",
    "https://eleuther.ai",
    "https://openrouter.ai",
    "https://langchain.com",
    "https://weightsandbiases.com",
    "https://mlflow.org",

    # Science / recherche
    "https://nature.com",
    "https://science.org",
    "https://sciencedirect.com",
    "https://springer.com",
    "https://ieee.org",
    "https://acm.org",
    "https://semanticscholar.org",
    "https://scholar.google.com",
    "https://arxiv.org",
    "https://researchgate.net",
    "https://jstor.org",
    "https://zenodo.org",

    # Données
    "https://data.gov",
    "https://data.europa.eu",
    "https://commoncrawl.org",
    "https://kaggle.com/datasets",
    "https://huggingface.co/datasets",

    # Cloud / infra
    "https://oracle.com",
    "https://linode.com",
    "https://hetzner.com",
    "https://ovhcloud.com",
    "https://contabo.com",
    "https://vultr.com",
    "https://akamai.com",
    "https://fastly.com",

    # DevOps
    "https://dockerhub.com",
    "https://hub.docker.com",
    "https://kubernetes.io",
    "https://helm.sh",
    "https://istio.io",
    "https://grafana.com",
    "https://prometheus.io",
    "https://elastic.co",
    "https://ansible.com",
    "https://terraform.io",
    "https://packer.io",
    "https://vaultproject.io",
    "https://consul.io",

    # Réseaux
    "https://openvpn.net",
    "https://wireguard.com",
    "https://tailscale.com",
    "https://zerotier.com",
    "https://mikrotik.com",
    "https://cisco.com",
    "https://juniper.net",

    # Hardware
    "https://raspberrypi.com",
    "https://arduino.cc",
    "https://espressif.com",
    "https://stmicroelectronics.com",
    "https://xilinx.com",
    "https://amd.com",
    "https://intel.com",
    "https://nvidia.com",
    "https://arm.com",

    # Game dev
    "https://opengl.org",
    "https://vulkan.org",
    "https://learnopengl.com",
    "https://gamedev.net",
    "https://gdevelop.io",
    "https://monogame.net",
    "https://love2d.org",
    "https://raylib.com",

    # Jeux
    "https://steamdb.info",
    "https://moddb.com",
    "https://curseforge.com",
    "https://planetminecraft.com",
    "https://spigotmc.org",
    "https://papermc.io",
    "https://modrinth.com",

    # Streaming / vidéo
    "https://vimeo.com",
    "https://dailymotion.com",
    "https://odysee.com",
    "https://rumble.com",
    "https://peer.tube",

    # Fediverse
    "https://mastodon.social",
    "https://lemmy.world",
    "https://kbin.social",
    "https://joinpeertube.org",
    "https://diasporafoundation.org",

    # Blogs tech
    "https://news.ycombinator.com",
    "https://lobste.rs",
    "https://dev.to",
    "https://hashnode.com",
    "https://medium.com",
    "https://substack.com",
    "https://techcrunch.com",
    "https://arstechnica.com",
    "https://theverge.com",
    "https://wired.com",

    # Privacy
    "https://eff.org",
    "https://privacyguides.org",
    "https://privacytools.io",
    "https://torproject.org",
    "https://riseup.net",

    # Cartographie
    "https://openstreetmap.org",
    "https://wikimapia.org",
    "https://geonames.org",

    # Archives
    "https://archive.org",
    "https://archive.ph",
    "https://openlibrary.org",
    "https://projectgutenberg.org",

    # APIs
    "https://rapidapi.com",
    "https://postman.com",
    "https://swagger.io",
    "https://graphql.org",
    "https://grpc.io",

    # Finance / crypto
    "https://kraken.com",
    "https://bybit.com",
    "https://okx.com",
    "https://coingecko.com",
    "https://tradingview.com",

    # Shopping
    "https://newegg.com",
    "https://bestbuy.com",
    "https://walmart.com",
    "https://target.com",
    "https://ikea.com",

    # Education
    "https://coursera.org",
    "https://edx.org",
    "https://udemy.com",
    "https://codecademy.com",
    "https://khanacademy.org",
    "https://freecodecamp.org",

    # Messagerie
    "https://matrix.org",
    "https://element.io",
    "https://revolt.chat",
    "https://guilded.gg",

    # Self-hosting
    "https://yunohost.org",
    "https://umbrel.com",
    "https://freenas.org",
    "https://truenas.com",
    "https://nextcloud.com",

    # Search engines
    "https://startpage.com",
    "https://searx.space",
    "https://qwant.com",
    "https://ecosia.org",

    # Torrent / partage
    "https://fosstorrents.com",
    "https://academictorrents.com",

    # Robots / web
    "https://commoncrawl.org",
    "https://schema.org",
    "https://w3c.org",
    "https://whatwg.org",

    # CDN / performance
    "https://jsdelivr.com",
    "https://unpkg.com",
    "https://cdnjs.com",

    # Fonts
    "https://fonts.google.com",
    "https://fontawesome.com",

    # Images
    "https://unsplash.com",
    "https://pexels.com",
    "https://pixabay.com",

    # Audio
    "https://freesound.org",
    "https://jamendo.com",

    # 3D
    "https://sketchfab.com",
    "https://thingiverse.com",
    "https://blender.org",

    # OSINT
    "https://intelx.io",
    "https://osintframework.com",
    "https://haveibeenpwned.com",

    # Satellites / espace
    "https://spacex.com",
    "https://starlink.com",
    "https://esa.int",
    "https://jpl.nasa.gov",

    # Santé
    "https://nih.gov",
    "https://cdc.gov",
    "https://ema.europa.eu",

    # Gouvernement
    "https://europa.eu",
    "https://gov.uk",
    "https://service-public.fr",
    "https://whitehouse.gov",

    # Web archi
    "https://nginx.org",
    "https://apache.org",
    "https://lighttpd.net",
    "https://caddyserver.com",

    # Bases de données
    "https://mariadb.org",
    "https://influxdata.com",
    "https://cassandra.apache.org",
    "https://neo4j.com",
    "https://clickhouse.com",

    # Navigateurs
    "https://opera.com",
    "https://brave.com",
    "https://vivaldi.com",
    "https://floorp.app",

    # Email
    "https://proton.me",
    "https://tutanota.com",
    "https://mailbox.org",
    "https://fastmail.com",

    # Password managers
    "https://bitwarden.com",
    "https://1password.com",
    "https://keepass.info",

    # Frameworks
    "https://react.dev",
    "https://vuejs.org",
    "https://svelte.dev",
    "https://angular.dev",
    "https://nextjs.org",
    "https://nuxt.com",
    "https://remix.run",

    # CSS / frontend
    "https://tailwindcss.com",
    "https://getbootstrap.com",
    "https://bulma.io",
    "https://sass-lang.com",

    # Electronique
    "https://adafruit.com",
    "https://sparkfun.com",
    "https://hackaday.com",

    # Wiki / knowledge
    "https://wikidata.org",
    "https://wikivoyage.org",
    "https://wiktionary.org",
    "https://fandom.com",
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
