# Ciro Chamleon 🦎

Adaptive Network Telemetry & Distributed Node Benchmarking Suite.

## Cara penyaringan

Setiap jam (`scout_engine.py`):

1. **Uji ulang vault.** Proxy yang gagal masuk standby. Kalau gagal `MAX_FAIL_STREAK` (3) kali berturut-turut, dibuang.
2. **Kumpulkan kandidat baru** dari ±35 sumber. Entri yang formatnya rusak, IP privat, atau sudah ada di vault dilewati.
3. **Cek port TCP** (2 detik) untuk menyingkirkan yang jelas mati.
4. **Uji HTTPS** ke `cdn-cgi/trace` Cloudflare lewat proxy, dengan sertifikat diverifikasi (proxy MITM otomatis gagal). Dites 3x, harus lolos minimal 2x, median latensi ≤ 4 detik.
5. **Cek ISP dari exit IP** (IP yang benar-benar terlihat oleh website, bukan IP proxy) via ip-api batch. Hosting/datacenter dibuang.
6. **Tes Tier 1** (StockX/Cloudflare) untuk proxy yang lolos.

`retest_engine.py` hanya menjalankan langkah 1 dan 6.

## Hasil

| File | Isi |
|---|---|
| `usable/all.txt` | Semua proxy siap pakai, satu per baris (`proto://ip:port`) |
| `usable/http.txt`, `usable/socks4.txt`, `usable/socks5.txt` | Dipisah per protokol |
| `residential_vault.txt` | Siap pakai + info negara, ISP, exit IP, latensi, tingkat sukses |
| `residential_vault.json` | Data lengkap, termasuk node standby |

Latensi diukur dari runner GitHub Actions (AS), bukan dari lokasi kamu.
