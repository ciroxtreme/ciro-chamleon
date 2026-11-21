import ipaddress
import json
import os
import socket
import statistics
import time
import urllib.request

from curl_cffi import requests as cffi_requests

VAULT_FILE = "residential_vault.txt"
JSON_VAULT_FILE = "residential_vault.json"
USABLE_DIR = "usable"

TRACE_URLS = ("https://www.cloudflare.com/cdn-cgi/trace", "https://1.1.1.1/cdn-cgi/trace")
PROTOCOLS = ("http", "https", "socks4", "socks5")

TCP_TIMEOUT = 2.0
PROBE_TIMEOUT = 6.0
ROUNDS = 3
MIN_SUCCESS = 2
MAX_LATENCY = 4.0
MAX_FAIL_STREAK = 3

DC_KEYWORDS = [
    "hosting", "cloud", "server", "vps", "datacenter", "data center", "digitalocean",
    "ovh", "hetzner", "amazon", "aws", "google", "alibaba", "linode", "akamai",
    "choopa", "vultr", "m247", "leaseweb", "contabo", "oracle", "microsoft", "azure",
    "zenlayer", "performive", "bitcommand", "tencent", "huawei", "colocrossing",
]


def now_utc():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def normalize(raw):
    """Return 'proto://host:port' or None if the entry is malformed or not public."""
    s = raw.strip().split()[0] if raw.strip() else ""
    if not s or s.startswith("#"):
        return None
    proto = "http"
    if "://" in s:
        proto, s = s.split("://", 1)
        proto = proto.lower()
    if proto not in PROTOCOLS:
        return None
    if "@" in s:
        return None
    s = s.split("/")[0]
    if s.count(":") != 1:
        return None
    host, port = s.split(":")
    try:
        ip = ipaddress.ip_address(host)
        port = int(port)
    except ValueError:
        return None
    if not ip.is_global or not (0 < port < 65536):
        return None
    if proto == "https":
        proto = "http"
    return f"{proto}://{host}:{port}"


def split_proxy(proxy):
    proto, rest = proxy.split("://", 1)
    host, port = rest.rsplit(":", 1)
    return proto, host, int(port)


def tcp_open(proxy):
    _, host, port = split_proxy(proxy)
    try:
        with socket.create_connection((host, port), timeout=TCP_TIMEOUT):
            return True
    except OSError:
        return False


def parse_trace(text):
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def fetch_trace(proxy=None, timeout=PROBE_TIMEOUT):
    proxies = {"http": proxy, "https": proxy} if proxy else None
    for url in TRACE_URLS:
        t0 = time.time()
        try:
            r = cffi_requests.get(url, proxies=proxies, timeout=timeout, verify=True,
                                  http_version="v1")
        except Exception:
            continue
        dt = time.time() - t0
        if r.status_code != 200:
            continue
        trace = parse_trace(r.text)
        if trace.get("ip") and trace.get("visit_scheme") == "https":
            return trace, dt
    return None, None


def get_runner_ip():
    try:
        trace, _ = fetch_trace()
        return trace.get("ip") if trace else None
    except Exception:
        return None


def probe(proxy, runner_ip, rounds=ROUNDS, min_success=MIN_SUCCESS):
    """HTTPS-through-proxy test (cert verified, so MITM proxies fail).

    Needs `min_success` of `rounds`; stops early once that is impossible.
    Returns dict with exit_ip/latency/success_rate or None.
    """
    latencies, exit_ips = [], set()
    for i in range(rounds):
        trace, dt = fetch_trace(proxy)
        if trace and trace["ip"] != runner_ip:
            latencies.append(dt)
            exit_ips.add(trace["ip"])
        if rounds - (i + 1) + len(latencies) < min_success:
            return None
    if len(latencies) < min_success:
        return None
    latency = round(statistics.median(latencies), 2)
    if latency > MAX_LATENCY:
        return None
    return {
        "exit_ip": sorted(exit_ips)[0],
        "rotating": len(exit_ips) > 1,
        "latency": latency,
        "success_rate": round(len(latencies) / rounds, 2),
    }


def lookup_ips(ips):
    """ip-api.com batch lookup (100 IPs/request, 15 requests/min on the free tier)."""
    fields = "status,query,country,countryCode,isp,org,as,hosting,mobile,proxy"
    ips = sorted(set(ips))
    result = {}
    for i in range(0, len(ips), 100):
        chunk = ips[i:i + 100]
        body = json.dumps(chunk).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    f"http://ip-api.com/batch?fields={fields}",
                    data=body,
                    headers={"Content-Type": "application/json", "User-Agent": "ciro-chamleon"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    remaining = int(resp.headers.get("X-Rl", "1"))
                    reset = int(resp.headers.get("X-Ttl", "60"))
                    for row in json.loads(resp.read().decode()):
                        if row.get("status") == "success":
                            result[row["query"]] = row
                if remaining <= 0:
                    time.sleep(reset + 1)
                break
            except Exception as e:
                print(f"⚠️  ip-api batch gagal (percobaan {attempt + 1}): {e}")
                time.sleep(5 * (attempt + 1))
    return result


def is_residential(info):
    if not info or info.get("hosting"):
        return False
    text = f"{info.get('isp', '')} {info.get('org', '')} {info.get('as', '')}".lower()
    return not any(kw in text for kw in DC_KEYWORDS)


def check_holy_grail(proxy):
    try:
        r = cffi_requests.get(
            "https://stockx.com",
            proxies={"http": proxy, "https": proxy},
            impersonate="chrome124",
            timeout=8.0,
        )
        return r.status_code == 200 and "challenges.cloudflare.com" not in r.text
    except Exception:
        return False


def load_vault():
    if not os.path.exists(JSON_VAULT_FILE):
        return []
    try:
        with open(JSON_VAULT_FILE) as f:
            return json.load(f)
    except Exception as e:
        print("⚠️  Gagal baca vault json:", e)
        return []


def save_vault(nodes):
    alive = [n for n in nodes if n.get("fail_streak", 0) == 0]
    alive.sort(key=lambda n: (not n.get("holy_grail"), n.get("latency", 999)))
    standby = [n for n in nodes if n.get("fail_streak", 0) > 0]
    holy = [n for n in alive if n.get("holy_grail")]
    active = [n for n in alive if not n.get("holy_grail")]

    with open(JSON_VAULT_FILE, "w") as f:
        json.dump(alive + standby, f, indent=2)

    def line(n, tag=""):
        rot = " [ROTATING]" if n.get("rotating") else ""
        mob = " [MOBILE]" if n.get("mobile") else ""
        return (f"{n['proxy']} # [{n.get('country')}] {n.get('isp')} | exit {n.get('exit_ip')} "
                f"({n.get('latency')}s, {int(n.get('success_rate', 0) * 100)}%){mob}{rot}{tag}\n")

    with open(VAULT_FILE, "w") as f:
        f.write("# ========================================================\n")
        f.write("# CIRO CHAMLEON - MULTI-TIER RESIDENTIAL VAULT\n")
        f.write(f"# Siap Pakai: {len(alive)} Proxies | Terakhir Uji: {now_utc()}\n")
        f.write("# Semua lolos: HTTPS (sertifikat valid), exit IP residential, stabil >= "
                f"{MIN_SUCCESS}/{ROUNDS} percobaan\n")
        f.write("# Latensi diukur dari runner GitHub Actions (bukan dari lokasi kamu)\n")
        f.write("# ========================================================\n\n")
        f.write(f"# --- TIER 1: HOLY GRAIL ({len(holy)} IP) - lolos tes StockX/Cloudflare ---\n")
        for n in holy:
            f.write(line(n, " [HOLY_GRAIL]"))
        if not holy:
            f.write("# (kosong)\n")
        f.write(f"\n# --- TIER 2: ACTIVE ({len(active)} IP) ---\n")
        for n in active:
            f.write(line(n))

    os.makedirs(USABLE_DIR, exist_ok=True)
    groups = {"all": alive}
    for proto in ("http", "socks4", "socks5"):
        groups[proto] = [n for n in alive if n["proxy"].startswith(proto + "://")]
    for name, items in groups.items():
        with open(os.path.join(USABLE_DIR, f"{name}.txt"), "w") as f:
            f.writelines(n["proxy"] + "\n" for n in items)
    print(f"💾 Vault disimpan: {len(alive)} siap pakai ({len(holy)} holy grail), {len(standby)} standby.")
