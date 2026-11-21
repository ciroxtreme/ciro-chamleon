import concurrent.futures

import chamleon_core as core


def retest(vault, runner_ip):
    print(f"🩺 Uji ulang {len(vault)} node di vault...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
        results = list(ex.map(lambda n: core.probe(n["proxy"], runner_ip), vault))

    passed = [(n, r) for n, r in zip(vault, results) if r]
    info = core.lookup_ips(r["exit_ip"] for _, r in passed)

    kept = []
    for node, res in zip(vault, results):
        if res and core.is_residential(info.get(res["exit_ip"])):
            meta = info[res["exit_ip"]]
            node.update(res)
            node.update({
                "country": meta.get("country"),
                "isp": meta.get("isp"),
                "asn": meta.get("as"),
                "mobile": meta.get("mobile"),
                "last_ok": core.now_utc(),
                "fail_streak": 0,
            })
            kept.append(node)
        elif res:
            print(f"🏢 {node['proxy']} exit {res['exit_ip']} bukan residential, dibuang.")
        else:
            node["fail_streak"] = node.get("fail_streak", 0) + 1
            if node["fail_streak"] < core.MAX_FAIL_STREAK:
                kept.append(node)

    alive = [n for n in kept if n["fail_streak"] == 0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        for node, ok in zip(alive, ex.map(lambda n: core.check_holy_grail(n["proxy"]), alive)):
            node["holy_grail"] = ok
    for n in kept:
        n.pop("host", None)
        n.pop("port", None)
        if n["fail_streak"]:
            n["holy_grail"] = False

    print(f"📊 Lolos: {len(alive)} | standby (gagal sementara): {len(kept) - len(alive)} | "
          f"dibuang: {len(vault) - len(kept)}")
    return kept


def main():
    vault = core.load_vault()
    if not vault:
        print("❌ Vault kosong.")
        return
    runner_ip = core.get_runner_ip()
    print(f"🛰️  IP runner: {runner_ip}")
    core.save_vault(retest(vault, runner_ip))


if __name__ == "__main__":
    main()
