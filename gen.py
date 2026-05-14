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
NEW_NODES_PER_RUN = 2500
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

    "https://google.com",
    "https://youtube.com",
    "https://facebook.com",
    "https://twitter.com",
    "https://instagram.com",
    "https://tiktok.com",
    "https://linkedin.com",
    "https://bing.com",
    "https://duckduckgo.com",
    "https://yahoo.com",

    "https://amazon.com",
    "https://ebay.com",
    "https://aliexpress.com",
    "https://etsy.com",
    "https://shopify.com",

    "https://netflix.com",
    "https://hulu.com",
    "https://disneyplus.com",
    "https://primevideo.com",
    "https://crunchyroll.com",

    "https://mozilla.org",
    "https://gnu.org",
    "https://kernel.org",
    "https://debian.org",
    "https://ubuntu.com",
    "https://archlinux.org",
    "https://fedora.org",

    "https://cloudflare.com",
    "https://vercel.com",
    "https://digitalocean.com",
    "https://aws.amazon.com",
    "https://azure.microsoft.com",
    "https://cloud.google.com",

    "https://openai.com",
    "https://anthropic.com",
    "https://deepmind.google",
    "https://huggingface.co",

    "https://npmjs.com",
    "https://pypi.org",
    "https://rubygems.org",
    "https://maven.apache.org",

    "https://apache.org",
    "https://nginx.org",
    "https://mysql.com",
    "https://postgresql.org",
    "https://sqlite.org",
    "https://redis.io",
    "https://mongodb.com",

    "https://unity.com",
    "https://unrealengine.com",
    "https://godotengine.org",

    "https://roblox.com",
    "https://minecraft.net",
    "https://fortnite.com",
    "https://leagueoflegends.com",
    "https://valorant.com",
    "https://steamcommunity.com",
    "https://store.steampowered.com",

    "https://bbc.com",
    "https://cnn.com",
    "https://nytimes.com",
    "https://theguardian.com",
    "https://lemonde.fr",
    "https://bfmtv.com",

    "https://who.int",
    "https://un.org",
    "https://nasa.gov",
    "https://esa.int",
    "https://noaa.gov",

    "https://spotify.com",
    "https://soundcloud.com",
    "https://deezer.com",
    "https://bandcamp.com",

    "https://imgur.com",
    "https://pinterest.com",
    "https://flickr.com",

    "https://wordpress.com",
    "https://medium.com",
    "https://substack.com",

    "https://w3.org",
    "https://ietf.org",
    "https://icann.org",

    "https://rust-lang.org",
    "https://go.dev",
    "https://nodejs.org",
    "https://php.net",
    "https://java.com",

    "https://stackoverflow.blog",
    "https://dev.to",
    "https://hashnode.com",

    "https://kickstarter.com",
    "https://patreon.com",
    "https://buymeacoffee.com",

    "https://canva.com",
    "https://figma.com",
    "https://adobe.com",

    "https://trello.com",
    "https://notion.so",
    "https://slack.com",
    "https://discord.com",

    "https://openstreetmap.org",
    "https://maps.google.com",
    "https://earth.google.com",

    "https://speedtest.net",
    "https://virustotal.com",
    "https://shodan.io",
    "https://censys.io",

    "https://archive.org",
    "https://waybackmachine.org",

    "https://coinmarketcap.com",
    "https://binance.com",
    "https://coinbase.com",

    "https://tesla.com",
    "https://spacex.com",
    "https://starlink.com",

    "https://airbnb.com",
    "https://booking.com",
    "https://tripadvisor.com",

    "https://imdb.com",
    "https://rottentomatoes.com",

    "https://stackoverflow.com",
    "https://superuser.com",
    "https://serverfault.com",

    "https://mathworks.com",
    "https://wolframalpha.com",

    "https://mit.edu",
    "https://stanford.edu",
    "https://harvard.edu",
    "https://ox.ac.uk",
    "https://cam.ac.uk",

    "https://proton.me",
    "https://mega.nz",
    "https://dropbox.com",
    "https://onedrive.live.com",
    "https://drive.google.com",

    "https://telegram.org",
    "https://whatsapp.com",
    "https://signal.org",

    "https://twitch.tv",
    "https://kick.com",

    "https://roblox.com",
    "https://epicgames.com",
    "https://riotgames.com",

    "https://docker.com",
    "https://kubernetes.io",

    "https://stackoverflow.com",
    "https://github.io",

    "https://python.org",
    "https://perl.org",
    "https://lua.org",

    "https://mozilla.org",
    "https://brave.com",
    "https://vivaldi.com",

    "https://cloudflare.com",
    "https://akamai.com",
    "https://fastly.com",

    "https://paypal.com",
    "https://stripe.com",
    "https://wise.com",

    "https://weather.com",
    "https://accuweather.com",

    "https://nationalgeographic.com",
    "https://science.org",

    "https://reuters.com",
    "https://apnews.com",

    "https://github.com",
    "https://gitlab.com",
    "https://bitbucket.org",

    "https://npmjs.com",
    "https://pypi.org",
    "https://crates.io",

    "https://stackoverflow.com",
    "https://superuser.com",
    "https://serverfault.com",
        "https://forbes.com",
    "https://bloomberg.com",
    "https://marketwatch.com",
    "https://investopedia.com",
    "https://morningstar.com",

    "https://wired.com",
    "https://techcrunch.com",
    "https://thenextweb.com",
    "https://arstechnica.com",
    "https://theverge.com",

    "https://ign.com",
    "https://gamespot.com",
    "https://pcgamer.com",
    "https://kotaku.com",
    "https://polygon.com",

    "https://xda-developers.com",
    "https://gsmarena.com",
    "https://android.com",
    "https://apple.com",
    "https://developer.apple.com",

    "https://intel.com",
    "https://amd.com",
    "https://nvidia.com",
    "https://qualcomm.com",
    "https://arm.com",

    "https://openbsd.org",
    "https://freebsd.org",
    "https://netbsd.org",

    "https://rust-lang.org",
    "https://ziglang.org",
    "https://crystal-lang.org",
    "https://elixir-lang.org",
    "https://clojure.org",

    "https://spring.io",
    "https://django-project.com",
    "https://flask.palletsprojects.com",
    "https://laravel.com",
    "https://symfony.com",

    "https://ansible.com",
    "https://terraform.io",
    "https://puppet.com",
    "https://chef.io",

    "https://grafana.com",
    "https://prometheus.io",
    "https://elastic.co",
    "https://kibana.dev",
    "https://logstash.net",

    "https://cloudflarestatus.com",
    "https://downdetector.com",
    "https://isitdownrightnow.com",

    "https://mozilla.org",
    "https://chromium.org",
    "https://webkit.org",

    "https://gnu.org",
    "https://fsf.org",
    "https://opensource.org",

    "https://coursera.org",
    "https://udemy.com",
    "https://edx.org",
    "https://khanacademy.org",
    "https://codecademy.com",

    "https://towardsdatascience.com",
    "https://kaggle.com",
    "https://paperswithcode.com",
    "https://arxiv.org",

    "https://nvidia.com",
    "https://geforce.com",
    "https://ati.com",

    "https://dockerhub.com",
    "https://hub.docker.com",
    "https://quay.io",

    "https://mailchimp.com",
    "https://sendgrid.com",
    "https://postmarkapp.com",

    "https://stripe.com",
    "https://squareup.com",
    "https://adyen.com",

    "https://bbc.co.uk",
    "https://france24.com",
    "https://euronews.com",
    "https://aljazeera.com",
    "https://dw.com",

    "https://weather.gov",
    "https://meteo.fr",
    "https://meteofrance.com",

    "https://stackoverflow.com",
    "https://superuser.com",
    "https://serverfault.com",
    "https://askubuntu.com",
    "https://mathoverflow.net",

    "https://unity.com",
    "https://unrealengine.com",
    "https://cryengine.com",

    "https://riotgames.com",
    "https://blizzard.com",
    "https://ea.com",
    "https://ubisoft.com",
    "https://bethesda.net",

    "https://epicgames.com",
    "https://rockstargames.com",
    "https://cdprojekt.com",

    "https://soundcloud.com",
    "https://mixcloud.com",
    "https://last.fm",
    "https://tidal.com",

    "https://pixabay.com",
    "https://pexels.com",
    "https://unsplash.com",

    "https://stackoverflow.com",
    "https://githubstatus.com",

    "https://python.org",
    "https://numpy.org",
    "https://pandas.pydata.org",
    "https://scipy.org",
    "https://matplotlib.org",

    "https://tensorflow.org",
    "https://pytorch.org",
    "https://keras.io",

    "https://openstreetmap.org",
    "https://wikidata.org",
    "https://wikivoyage.org",
    "https://wikinews.org",

    "https://mozilla.org",
    "https://vivaldi.com",
    "https://opera.com",

    "https://paypal.com",
    "https://skrill.com",
    "https://revolut.com",

    "https://cloudflare.com",
    "https://fastly.com",
    "https://akamai.com",

    "https://namecheap.com",
    "https://godaddy.com",
    "https://gandi.net",

    "https://riot.im",
    "https://matrix.org",
    "https://element.io",

    "https://proton.me",
    "https://tutanota.com",
    "https://mailbox.org",

    "https://bitwarden.com",
    "https://1password.com",
    "https://lastpass.com",

    "https://mozilla.org",
    "https://getbootstrap.com",
    "https://tailwindcss.com",
    "https://sass-lang.com",
    "https://lesscss.org",

    "https://jquery.com",
    "https://react.dev",
    "https://vuejs.org",
    "https://svelte.dev",
    "https://angular.io",

    "https://threejs.org",
    "https://babylonjs.com",
    "https://pixijs.com",

    "https://openai.com",
    "https://anthropic.com",
    "https://cohere.com",
    "https://stability.ai",

    "https://mozilla.org",
    "https://brave.com",
    "https://torproject.org",

    "https://wikileaks.org",
    "https://eff.org",
    "https://privacytools.io",

    "https://archive.org",
    "https://openlibrary.org",
    "https://projectgutenberg.org",

    "https://spotify.com",
    "https://applemusic.com",
    "https://youtube.com/music",

    "https://twitch.tv",
    "https://dlive.tv",
    "https://trovo.live",

    "https://roblox.com",
    "https://minecraft.net",
    "https://terraria.org",
    "https://rust.facepunch.com",
    "https://playvalorant.com",

    "https://intel.com",
    "https://amd.com",
    "https://nvidia.com",

    "https://tesla.com",
    "https://spacex.com",
    "https://starlink.com",

    "https://who.int",
    "https://cdc.gov",
    "https://ema.europa.eu",

    "https://openvpn.net",
    "https://wireguard.com",
    "https://tailscale.com",

    "https://mozilla.org",
    "https://chromium.org",
    "https://webkit.org",
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
