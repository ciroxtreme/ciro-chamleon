import urllib.request
import json
import time
import socket
import concurrent.futures
import os
import sys

VAULT_FILE = "residential_vault.txt"
JSON_VAULT_FILE = "residential_vault.json"

print("🦎 [CIRO CHAMLEON - MASS SCANNER ULTRA] Mengunduh dari Seluruh Repo Dunia...")

# 35+ SUMBER REPO PROXY DUNIA (TERMASUK ROOSTERKID & CASPER-TECH)
SOURCES_TXT = [
    # RoosterKid (Baru)
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",

    # Rekomendasi Tuan Ciro:
    "https://raw.githubusercontent.com/claude89757/free_https_proxies/main/https_proxies.txt",
    "https://raw.githubusercontent.com/claude89757/free_https_proxies/main/isz_https_proxies.txt",
    "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/main/All_proxies.txt",
    "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/main/http_proxies.txt",
    "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/main/socks4_proxies.txt",
    "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/main/socks5_proxies.txt",
    "https://raw.githubusercontent.com/vmheaven/VMHeaven.io-Free-Proxy-List/main/allproxy.txt",
    "https://raw.githubusercontent.com/vmheaven/VMHeaven.io-Free-Proxy-List/main/http.txt",
    "https://raw.githubusercontent.com/vmheaven/VMHeaven.io-Free-Proxy-List/main/https.txt",
    "https://raw.githubusercontent.com/vmheaven/VMHeaven.io-Free-Proxy-List/main/socks4.txt",
    "https://raw.githubusercontent.com/vmheaven/VMHeaven.io-Free-Proxy-List/main/socks5.txt",
    "https://raw.githubusercontent.com/proxio-io/proxy-list/main/all.txt",
    "https://raw.githubusercontent.com/proxio-io/proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/proxio-io/proxy-list/main/socks5.txt",
    "https://raw.githubusercontent.com/proxygenerator1/ProxyGenerator/main/telegramProxys.txt",
    "https://raw.githubusercontent.com/proxygenerator1/ProxyGenerator/main/MostStable/HTTP.txt",
    "https://raw.githubusercontent.com/proxygenerator1/ProxyGenerator/main/MostStable/SOCKS5.txt",
    "https://raw.githubusercontent.com/6yyn/free-proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/6yyn/free-proxy-list/main/https.txt",
    "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/all-proxies.txt",
    "https://raw.githubusercontent.com/FusionProxies/free-proxy-list/main/proxies/all.txt",
    "https://raw.githubusercontent.com/FusionProxies/free-proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/FusionProxies/free-proxy-list/main/proxies/socks5.txt",

    # Repo Utama:
    "https://raw.githubusercontent.com/solproxy/sol-free-proxy-list/main/all.txt",
    "https://raw.githubusercontent.com/solproxy/sol-free-proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/ProxyScrape/free-proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/ProxyScrape/free-proxy-list/main/socks5.txt",
    "https://raw.githubusercontent.com/ProxyScrape/free-proxy-list/main/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
]

SOURCES_JSON = [
    # Casper-Tech-ke (Baru)
    "https://raw.githubusercontent.com/Casper-Tech-ke/casper-free-proxies/main/files/proxies.json"
]

DC_KEYWORDS = [
    "hosting", "cloud", "server", "vps", "datacenter", "digitalocean",
    "ovh", "hetzner", "amazon", "aws", "google", "alibaba", "linode",
    "choopa", "m247", "leaseweb", "contabo", "oracle", "microsoft", "azure"
]

# 1. BACA PENYIMPANAN BRANKAS YANG SUDAH ADA (ANTI-DUPLIKAT)
existing_proxies = set()
existing_data = []

if os.path.exists(JSON_VAULT_FILE):
    try:
        with open(JSON_VAULT_FILE, "r") as f:
            existing_data = json.load(f)
            for item in existing_data:
                existing_proxies.add(item.get("proxy"))
    except Exception as e:
        print("Warning read json vault:", e)

print(f"🏦 [PENYIMPANAN SAAT INI] Sudah tersimpan {len(existing_proxies)} proxy unik di brankas.")

# 2. AMBIL SEMUA PROXY BARU
raw_candidates = set()

# A. Unduh sumber TXT
for s in SOURCES_TXT:
    try:
        req = urllib.request.Request(s, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            lines = resp.read().decode("utf-8", errors="ignore").splitlines()
            for line in lines:
                l = line.strip()
                if l and not l.startswith("#"):
                    if "://" not in l:
                        l = "http://" + l
                    if l not in existing_proxies:
                        raw_candidates.add(l)
    except Exception:
        pass

# B. Unduh sumber JSON (Casper-Tech)
for s in SOURCES_JSON:
    try:
        req = urllib.request.Request(s, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pxs = data.get("proxies", [])
            for p in pxs:
                p = p.strip()
                if p:
                    if "://" not in p:
                        p = "http://" + p
                    if p not in existing_proxies:
                        raw_candidates.add(p)
    except Exception:
        pass

print(f"📦 Total target baru dari 35+ sumber: {len(raw_candidates)} node.")

def parse_node(url_str):
    proto = "http"
    clean = url_str
    if "://" in url_str:
        proto, clean = url_str.split("://", 1)
    parts = clean.split(":")
    return proto, parts[0], int(parts[1])

# Tahap 1: Tes TCP Connect Nyata
def test_tcp_alive(cand):
    try:
        proto, host, port = parse_node(cand)
        if host.startswith("10.") or host.startswith("192.168.") or host.startswith("127."):
            return None
        t0 = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        res = s.connect_ex((host, port))
        s.close()
        if res == 0:
            dt = round(time.time() - t0, 2)
            return (cand, host, port, proto, dt)
    except Exception:
        pass
    return None

all_pool = list(raw_candidates)
print(f"⚡ [Tahap 1] Memindai {len(all_pool)} kandidat baru dengan 200 THREAD PARALEL...")

live_nodes = []
with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
    results = executor.map(test_tcp_alive, all_pool)
    for r in results:
        if r:
            live_nodes.append(r)

print(f"🟢 [Tahap 1 Selesai] Ditemukan {len(live_nodes)} node aktif merespon TCP!")

# Tahap 2: Verifikasi ASN Residential Murni
def check_asn(node_item):
    cand, host, port, proto, latency = node_item
    try:
        req = urllib.request.Request(
            f"http://ip-api.com/json/{host}?fields=status,country,isp,org,as,hosting,mobile",
            headers={"User-Agent": "curl/7.68.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "success":
                return None
            
            is_dc = data.get("hosting", False)
            info_str = f"{data.get('isp','')} {data.get('org','')} {data.get('as','')}".lower()
            for kw in DC_KEYWORDS:
                if kw in info_str:
                    is_dc = True
                    break
            
            if not is_dc:
                return {
                    "proxy": cand,
                    "host": host,
                    "port": port,
                    "country": data.get("country"),
                    "isp": data.get("isp"),
                    "mobile": data.get("mobile"),
                    "latency": latency,
                    "added_at": time.strftime("%Y-%m-%d %H:%M:%S UTC")
                }
    except Exception:
        pass
    return None

print(f"🔍 [Tahap 2] Memverifikasi ASN Residential ISP...")
newly_found = []
with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
    results = executor.map(check_asn, live_nodes)
    for r in results:
        if r:
            newly_found.append(r)
            print(f"💎 [BARU!] {r['proxy']} | {r['country']} | {r['isp']} | {r['latency']}s")

print(f"\n🎉 HASIL PUTARAN INI:")
print(f"• Node Baru Ditemukan: {len(newly_found)}")

# 3. GABUNGKAN KE PENYIMPANAN LAMA (AKUMULASI ANTI-DUPLIKAT)
for item in newly_found:
    if item["proxy"] not in existing_proxies:
        existing_data.append(item)
        existing_proxies.add(item["proxy"])

total_saved = len(existing_data)
print(f"🏦 TOTAL TABUNGAN DI PENYIMPANAN SAAT INI: {total_saved} PROXY RESIDENTIAL!")

with open(JSON_VAULT_FILE, "w") as f:
    json.dump(existing_data, f, indent=2)

with open(VAULT_FILE, "w") as f:
    f.write(f"# ========================================================\n")
    f.write(f"# CIRO CHAMLEON - RESIDENTIAL VAULT STORAGE (ULTRA SOURCES)\n")
    f.write(f"# Total Akumulasi: {total_saved} Proxies Unik (Anti-Duplikat)\n")
    f.write(f"# Terakhir Diperbarui: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    f.write(f"# ========================================================\n\n")
    for r in existing_data:
        f.write(f"{r['proxy']} # [{r.get('country')}] {r.get('isp')} ({r.get('latency')}s)\n")

print(f"💾 File {VAULT_FILE} & {JSON_VAULT_FILE} berhasil diperbarui di repositori!")
