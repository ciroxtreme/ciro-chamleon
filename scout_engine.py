import urllib.request
import json
import time
import socket
import concurrent.futures
import os
import sys

VAULT_FILE = "residential_vault.txt"
JSON_VAULT_FILE = "residential_vault.json"

print("🦎 [CIRO CHAMLEON - MASS SCANNER] Memulai Scanning Skala Besar...")

# Sumber Massal
SOURCES = [
    # Solproxy
    "https://raw.githubusercontent.com/solproxy/sol-free-proxy-list/main/all.txt",
    "https://raw.githubusercontent.com/solproxy/sol-free-proxy-list/main/http.txt",
    # ProxyScrape
    "https://raw.githubusercontent.com/ProxyScrape/free-proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/ProxyScrape/free-proxy-list/main/socks5.txt",
    "https://raw.githubusercontent.com/ProxyScrape/free-proxy-list/main/socks4.txt",
    # Monosans & SpeedX
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
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

# 2. AMBIL SEMUA PROXY DARI SELURUH SUMBER SEKALIGUS
raw_candidates = set()
for s in SOURCES:
    try:
        req = urllib.request.Request(s, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            lines = resp.read().decode("utf-8", errors="ignore").splitlines()
            for line in lines:
                l = line.strip()
                if l and not l.startswith("#"):
                    if "://" not in l:
                        l = "http://" + l
                    # Buang yang sudah ada di brankas agar tidak boros waktu
                    if l not in existing_proxies:
                        raw_candidates.add(l)
    except Exception as e:
        print(f"Warning fetch {s}: {e}")

print(f"📦 Total target baru yang belum ada di brankas: {len(raw_candidates)} node.")

def parse_node(url_str):
    proto = "http"
    clean = url_str
    if "://" in url_str:
        proto, clean = url_str.split("://", 1)
    parts = clean.split(":")
    return proto, parts[0], int(parts[1])

# Tahap 1: Tes TCP Connect Nyata Cepat
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

# PINDAI SEMUA SEKALIGUS dengan 200 Thread Paralel
all_pool = list(raw_candidates)
print(f"⚡ [Tahap 1] Memindai {len(all_pool)} kandidat sekaligus dengan 200 THREAD PARALEL...")

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

# Simpan ke JSON Vault
with open(JSON_VAULT_FILE, "w") as f:
    json.dump(existing_data, f, indent=2)

# Simpan ke TXT Vault (Format Siap Pakai)
with open(VAULT_FILE, "w") as f:
    f.write(f"# ========================================================\n")
    f.write(f"# CIRO CHAMLEON - RESIDENTIAL VAULT STORAGE\n")
    f.write(f"# Total Akumulasi: {total_saved} Proxies Unik (Anti-Duplikat)\n")
    f.write(f"# Terakhir Diperbarui: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    f.write(f"# ========================================================\n\n")
    for r in existing_data:
        f.write(f"{r['proxy']} # [{r.get('country')}] {r.get('isp')} ({r.get('latency')}s)\n")

print(f"💾 File {VAULT_FILE} & {JSON_VAULT_FILE} berhasil diperbarui di repositori!")
