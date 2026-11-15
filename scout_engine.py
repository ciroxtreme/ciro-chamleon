import urllib.request
import json
import time
import socket
import concurrent.futures
import os
import sys

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "DUMMY_TELEGRAM_TOKEN_PROTECTED")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1936436999")
TARGET_COUNT = int(os.environ.get("TARGET_COUNT", "60"))

print("🦎 [CIRO CHAMLEON RADAR] Inisialisasi Penarikan Data Jaringan...")

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

def send_telegram_doc(filename, filepath, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    with open(filepath, "rb") as f:
        file_bytes = f.read()
        
    body = bytearray()
    # chat_id
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{CHAT_ID}\r\n".encode())
    # caption
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode())
    # file
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\nContent-Type: text/plain\r\n\r\n".encode())
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    
    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print("📤 Dokumen berhasil terkirim ke Telegram Tuan Ciro! Status:", r.status)
    except Exception as e:
        print("❌ Gagal kirim Telegram:", e)

# 1. Unduh Semua Sumber
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
                    raw_candidates.add(l)
    except Exception as e:
        print(f"Warning fetch {s}: {e}")

print(f"📦 Terkumpul {len(raw_candidates)} node mentah. Mulai penyaringan ganda...")

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
        s.settimeout(2.5)
        res = s.connect_ex((host, port))
        s.close()
        if res == 0:
            dt = round(time.time() - t0, 2)
            return (cand, host, port, proto, dt)
    except Exception:
        pass
    return None

import random
sample_pool = random.sample(list(raw_candidates), min(1200, len(raw_candidates)))
print(f"⚡ [Tahap 1] Menguji TCP handshake pada {len(sample_pool)} kandidat dengan 120 thread...")

live_nodes = []
with concurrent.futures.ThreadPoolExecutor(max_workers=120) as executor:
    results = executor.map(test_tcp_alive, sample_pool)
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
                    "latency": latency
                }
    except Exception:
        pass
    return None

print(f"🔍 [Tahap 2] Memverifikasi ASN Residential ISP...")
residential_winners = []
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    results = executor.map(check_asn, live_nodes)
    for r in results:
        if r:
            residential_winners.append(r)
            print(f"💎 [{len(residential_winners)}] {r['proxy']} | {r['country']} | {r['isp']} | {r['latency']}s")
            if len(residential_winners) >= TARGET_COUNT:
                break

print(f"\n🏆 SELESAI! Ditemukan {len(residential_winners)} IP Residential murni & hidup.")

# Simpan ke file teks rapi
out_file = "ciro_residential_nodes.txt"
with open(out_file, "w") as f:
    f.write(f"# ========================================================\n")
    f.write(f"# CIRO CHAMLEON - RESIDENTIAL VERIFIED NODES\n")
    f.write(f"# Total: {len(residential_winners)} Nodes Aktif Terverifikasi\n")
    f.write(f"# Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    f.write(f"# ========================================================\n\n")
    for r in residential_winners:
        f.write(f"{r['proxy']} # [{r['country']}] {r['isp']} ({r['latency']}s)\n")

# Kirim ke Telegram Tuan Ciro
caption = f"🦎 **CIRO CHAMLEON PANEN HASIL!**\n\n" \
          f"✅ Berhasil menyaring: **{len(residential_winners)} IP Residential Hidup!**\n" \
          f"⚡ Semua lolos uji TCP Handshake + verifikasi ISP Rumahan murni.\n" \
          f"📦 File dokumen terlampir siap pakai untuk scraping!"

if residential_winners:
    send_telegram_doc(out_file, out_file, caption)
else:
    print("Zero residential found in current run.")
