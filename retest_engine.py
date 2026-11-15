import json
import time
import socket
import concurrent.futures
import os
import sys

VAULT_FILE = "residential_vault.txt"
JSON_VAULT_FILE = "residential_vault.json"

print("🩺 [CIRO CHAMLEON - RE-TEST SANITIZER] Memulai Uji Ulang Seluruh Brankas...")

if not os.path.exists(JSON_VAULT_FILE):
    print("❌ File brankas json belum ada.")
    sys.exit(0)

with open(JSON_VAULT_FILE, "r") as f:
    vault_data = json.load(f)

total_before = len(vault_data)
print(f"📦 Total proxy yang akan diuji ulang kesehatannya: {total_before} IP...")

def parse_node(url_str):
    proto = "http"
    clean = url_str
    if "://" in url_str:
        proto, clean = url_str.split("://", 1)
    parts = clean.split(":")
    return proto, parts[0], int(parts[1])

def retest_node(item):
    cand = item.get("proxy")
    try:
        proto, host, port = parse_node(cand)
        t0 = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.5)
        res = s.connect_ex((host, port))
        s.close()
        if res == 0:
            dt = round(time.time() - t0, 2)
            item["latency"] = dt
            item["last_tested"] = time.strftime("%Y-%m-%d %H:%M:%S UTC")
            return item
    except Exception:
        pass
    return None

survivors = []
with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
    results = executor.map(retest_node, vault_data)
    for r in results:
        if r:
            survivors.append(r)
            print(f"🟢 [MASIH SEGAR!] {r['proxy']} ({r.get('country')} | {r['latency']}s)")

total_after = len(survivors)
total_dead = total_before - total_after
print(f"\n📊 HASIL RE-TEST & PEMBERSIHAN:")
print(f"• Total Awal: {total_before}")
print(f"• Node Mati Dibuang: {total_dead}")
print(f"• Node Segar Bertahan: {total_after}")

# Perbarui JSON Vault
with open(JSON_VAULT_FILE, "w") as f:
    json.dump(survivors, f, indent=2)

# Perbarui TXT Vault
with open(VAULT_FILE, "w") as f:
    f.write(f"# ========================================================\n")
    f.write(f"# CIRO CHAMLEON - RESIDENTIAL VAULT (RE-TESTED & CLEAN)\n")
    f.write(f"# Total Aktif Bersih: {total_after} Proxies\n")
    f.write(f"# Terakhir Diuji Ulang: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    f.write(f"# ========================================================\n\n")
    for r in survivors:
        f.write(f"{r['proxy']} # [{r.get('country')}] {r.get('isp')} ({r.get('latency')}s)\n")

print("💾 Brankas berhasil dibersihkan dari IP mati!")
