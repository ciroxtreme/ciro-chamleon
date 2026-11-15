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

VAULT_FILE = "residential_vault.txt"
JSON_VAULT_FILE = "residential_vault.json"

print("🩺 [CIRO CHAMLEON - MULTI-PROTOCOL PAYLOAD SANITIZER] Memulai Uji Transmisi Nyata...")
if HAS_SOCKS:
    print("⚡ Dukungan SOCKS4 & SOCKS5 aktif (via PySocks)!")
else:
    print("⚠️ PySocks tidak terpasang, hanya menguji HTTP/HTTPS.")

if not os.path.exists(JSON_VAULT_FILE):
    print("❌ File brankas json belum ada.")
    sys.exit(0)

with open(JSON_VAULT_FILE, "r") as f:
    vault_data = json.load(f)

total_before = len(vault_data)
print(f"📦 Total kandidat awal yang akan diuji beban nyata: {total_before} IP...")

def retest_node_payload(item):
    cand = item.get("proxy", "").strip()
    if not cand:
        return None
    
    try:
        t0 = time.time()
        # 1. Kasus SOCKS5
        if cand.startswith("socks5://"):
            if not HAS_SOCKS:
                return None
            raw = cand.replace("socks5://", "")
            host, port = raw.split(":")
            opener = urllib.request.build_opener(SocksiPyHandler(socks.SOCKS5, host, int(port)))
        # 2. Kasus SOCKS4
        elif cand.startswith("socks4://"):
            if not HAS_SOCKS:
                return None
            raw = cand.replace("socks4://", "")
            host, port = raw.split(":")
            opener = urllib.request.build_opener(SocksiPyHandler(socks.SOCKS4, host, int(port)))
        # 3. Kasus HTTP / HTTPS
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
                return item
    except Exception:
        pass
    return None

survivors = []
with concurrent.futures.ThreadPoolExecutor(max_workers=80) as executor:
    results = executor.map(retest_node_payload, vault_data)
    for r in results:
        if r:
            survivors.append(r)
            proto = r['proxy'].split("://")[0].upper()
            tier = "⚡ ELITE ULTRA" if r['latency'] < 0.8 else "🟢 FAST"
            print(f"[{tier}] [{proto}] {r['proxy']} ({r.get('country')} | {r['latency']}s)")

# Urutkan berdasarkan latensi tercepat ke terlambat
survivors.sort(key=lambda x: x.get("latency", 999))

total_after = len(survivors)
total_dead = total_before - total_after
print(f"\n📊 HASIL FILTER BEBAN NYATA:")
print(f"• Total Sebelum: {total_before} IP")
print(f"• Palsu / Lambat / Terblokir Dibuang: {total_dead} IP")
print(f"• Lolos Verifikasi Transmisi Data: {total_after} IP Murni Kencang & Responsif!")

# Simpan ke JSON
with open(JSON_VAULT_FILE, "w") as f:
    json.dump(survivors, f, indent=2)

# Simpan ke TXT dengan rincian Protokol
with open(VAULT_FILE, "w") as f:
    f.write(f"# ========================================================\n")
    f.write(f"# CIRO CHAMLEON - HIGH PERFORMANCE MULTI-PROTOCOL VAULT\n")
    f.write(f"# Total Bersih & Teruji Beban Nyata: {total_after} Proxies\n")
    f.write(f"# Mendukung: HTTP, HTTPS, SOCKS4, SOCKS5\n")
    f.write(f"# Terakhir Diuji Ulang: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    f.write(f"# Diurutkan dari yang Paling Kencang & Responsif (< 2.5s)\n")
    f.write(f"# ========================================================\n\n")
    for r in survivors:
        f.write(f"{r['proxy']} # [{r.get('country')}] {r.get('isp')} ({r.get('latency')}s)\n")

print("💾 Brankas berhasil disterilkan dan diurutkan berdasarkan kecepatan nyata!")
