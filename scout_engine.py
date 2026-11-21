import concurrent.futures
import json
import urllib.request

import chamleon_core as core
from retest_engine import retest

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
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
]

SOURCES_JSON = [
    # Casper-Tech-ke (Baru)
    "https://raw.githubusercontent.com/Casper-Tech-ke/casper-free-proxies/main/files/proxies.json"
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def collect_candidates(known):
    candidates = set()
    for url in SOURCES_TXT:
        try:
            for line in fetch(url).splitlines():
                p = core.normalize(line)
                if p and p not in known:
                    candidates.add(p)
        except Exception as e:
            print(f"⚠️  Sumber gagal: {url} ({e})")
    for url in SOURCES_JSON:
        try:
            for raw in json.loads(fetch(url)).get("proxies", []):
                p = core.normalize(raw)
                if p and p not in known:
                    candidates.add(p)
        except Exception as e:
            print(f"⚠️  Sumber gagal: {url} ({e})")
    return candidates


def scan(candidates, runner_ip):
    print(f"⚡ [Tahap 1] Cek port TCP {len(candidates)} kandidat...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=300) as ex:
        open_ports = [p for p, ok in zip(candidates, ex.map(core.tcp_open, candidates)) if ok]
    print(f"🔌 Port terbuka: {len(open_ports)}")

    print(f"🔐 [Tahap 2] Uji HTTPS {core.ROUNDS}x per proxy (harus lolos {core.MIN_SUCCESS}x)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=200) as ex:
        results = list(ex.map(lambda p: core.probe(p, runner_ip), open_ports))
    working = [(p, r) for p, r in zip(open_ports, results) if r]
    print(f"🟢 Lolos HTTPS & stabil: {len(working)}")

    print("🔍 [Tahap 3] Cek ISP dari exit IP (ip-api batch)...")
    info = core.lookup_ips(r["exit_ip"] for _, r in working)
    found = []
    for proxy, res in working:
        meta = info.get(res["exit_ip"])
        if not core.is_residential(meta):
            continue
        node = {"proxy": proxy, **res,
                "country": meta.get("country"), "isp": meta.get("isp"), "asn": meta.get("as"),
                "mobile": meta.get("mobile"), "added_at": core.now_utc(),
                "last_ok": core.now_utc(), "fail_streak": 0, "holy_grail": False}
        found.append(node)
        print(f"💎 [BARU] {proxy} | exit {res['exit_ip']} | {node['country']} | {node['isp']} | {res['latency']}s")
    return found


def main():
    runner_ip = core.get_runner_ip()
    print(f"🛰️  IP runner: {runner_ip}")
    vault = core.load_vault()
    print(f"🏦 Vault saat ini: {len(vault)} node")

    vault = retest(vault, runner_ip) if vault else []
    known = {n["proxy"] for n in vault}

    candidates = sorted(collect_candidates(known))
    print(f"📦 Kandidat baru: {len(candidates)}")
    new_nodes = scan(candidates, runner_ip)
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        for node, ok in zip(new_nodes, ex.map(lambda n: core.check_holy_grail(n["proxy"]), new_nodes)):
            node["holy_grail"] = ok

    core.save_vault(vault + new_nodes)


if __name__ == "__main__":
    main()
