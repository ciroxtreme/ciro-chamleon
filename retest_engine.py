import json
import time
import urllib.request
import concurrent.futures
import os
import sys

try:
    import socks
    from sockshandler import SocksiPyHandler
    HAS_SOCKS = True
except ImportError:
    HAS_SOCKS = False

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

VAULT_FILE = "residential_vault.txt"
JSON_VAULT_FILE = "residential_vault.json"

print("🩺 [CIRO CHAMLEON - TIERED PAYLOAD SANITIZER] Memulai Uji Transmisi & Pemisahan Kasta...")
if HAS_SOCKS:
    print("⚡ Dukungan SOCKS4 & SOCKS5 aktif (via PySocks)!")
if HAS_CFFI:
    print("🛡️ Engine Audit Suci (Bypass Cloudflare/StockX via curl_cffi) aktif!")

if not os.path.exists(JSON_VAULT_FILE):
    print("❌ File brankas json belum ada.")
    sys.exit(0)

with open(JSON_VAULT_FILE, "r") as f:
    vault_data = json.load(f)

total_before = len(vault_data)
print(f"📦 Total kandidat awal yang akan diuji beban nyata: {total_before} IP...")

def retest_node(item):
    cand = item.get("proxy", "").strip()
    if not cand:
        return None
    
    # 1. Tahap Verifikasi Keaktifan & Latensi Dasar
    try:
        t0 = time.time()
        if cand.startswith("socks5://"):
            if not HAS_SOCKS:
                return None
            raw = cand.replace("socks5://", "")
            host, port = raw.split(":")
            opener = urllib.request.build_opener(SocksiPyHandler(socks.SOCKS5, host, int(port)))
        elif cand.startswith("socks4://"):
            if not HAS_SOCKS:
                return None
            raw = cand.replace("socks4://", "")
            host, port = raw.split(":")
            opener = urllib.request.build_opener(SocksiPyHandler(socks.SOCKS4, host, int(port)))
        else:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': cand, 'https': cand}))
        
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')]
        
        # Batas timeout ketat 2.5 detik (hanya loloskan yang kencang & anti-bengong)
        with opener.open('http://cloudflare.com/cdn-cgi/trace', timeout=2.5) as res:
            content = res.read().decode('utf-8', errors='ignore')
            if 'colo=' in content or 'ip=' in content:
                dt = round(time.time() - t0, 2)
                item["latency"] = dt
                item["last_tested"] = time.strftime("%Y-%m-%d %H:%M:%S UTC")
                
                # 2. Tahap Uji Kasta: Tes Kesucian Melawan Cloudflare Anti-Bot (StockX / WAF)
                item["holy_grail"] = False
                if HAS_CFFI:
                    try:
                        r_cf = cffi_requests.get(
                            "https://stockx.com",
                            proxies={"http": cand, "https": cand},
                            impersonate="chrome124",
                            timeout=3.0,
                            verify=False
                        )
                        if r_cf.status_code == 200 and "challenges.cloudflare.com" not in r_cf.text:
                            item["holy_grail"] = True
                    except Exception:
                        pass
                
                return item
    except Exception:
        pass
    return None

survivors = []
with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
    results = executor.map(retest_node, vault_data)
    for r in results:
        if r:
            survivors.append(r)
            proto = r['proxy'].split("://")[0].upper()
            if r.get("holy_grail"):
                print(f"🌟 [TIER 1 - HOLY GRAIL] [{proto}] {r['proxy']} ({r.get('country')} | {r['latency']}s)")
            else:
                print(f"🟢 [TIER 2 - ACTIVE] [{proto}] {r['proxy']} ({r.get('country')} | {r['latency']}s)")

# Pisahkan menjadi 2 Kasta
holy_nodes = [x for x in survivors if x.get("holy_grail")]
active_nodes = [x for x in survivors if not x.get("holy_grail")]

holy_nodes.sort(key=lambda x: x.get("latency", 999))
active_nodes.sort(key=lambda x: x.get("latency", 999))

all_sorted = holy_nodes + active_nodes

total_after = len(all_sorted)
print(f"\n📊 HASIL AUDIT KASTA PROXY:")
print(f"• Total Aktif Lolos Uji: {total_after} IP")
print(f"• 🌟 Tier 1 (Holy Grail - Tembus Cloudflare/StockX): {len(holy_nodes)} IP")
print(f"• 🟢 Tier 2 (Active Warrior - Standar Kencang): {len(active_nodes)} IP")

# Simpan ke JSON
with open(JSON_VAULT_FILE, "w") as f:
    json.dump(all_sorted, f, indent=2)

# Simpan ke TXT dengan pemisah kasta yang sangat rapi
with open(VAULT_FILE, "w") as f:
    f.write(f"# ========================================================\n")
    f.write(f"# CIRO CHAMLEON - MULTI-TIER RESIDENTIAL VAULT\n")
    f.write(f"# Total Bersih: {total_after} Proxies | Terakhir Uji: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    f.write(f"# Mendukung: HTTP, HTTPS, SOCKS4, SOCKS5\n")
    f.write(f"# ========================================================\n\n")
    
    f.write(f"# --------------------------------------------------------\n")
    f.write(f"# 🌟 TIER 1: THE HOLY GRAIL ({len(holy_nodes)} IP)\n")
    f.write(f"# Lolos WAF Cloudflare / StockX (Bebas Dosa & Anti-Challenge)\n")
    f.write(f"# --------------------------------------------------------\n")
    if holy_nodes:
        for r in holy_nodes:
            f.write(f"{r['proxy']} # [{r.get('country')}] {r.get('isp')} ({r.get('latency')}s) [HOLY_GRAIL]\n")
    else:
        f.write(f"# (Sedang dipindai ulang oleh scout engine...)\n")
    f.write("\n")

    f.write(f"# --------------------------------------------------------\n")
    f.write(f"# 🟢 TIER 2: ACTIVE WARRIORS ({len(active_nodes)} IP)\n")
    f.write(f"# Kencang & Responsif (< 2.5s) - Sangat Cocok untuk Regular Scraping\n")
    f.write(f"# --------------------------------------------------------\n")
    for r in active_nodes:
        f.write(f"{r['proxy']} # [{r.get('country')}] {r.get('isp')} ({r.get('latency')}s)\n")

print("💾 Brankas bertingkat berhasil diperbarui dan dipisahkan kastanya!")
