"""SCRUM-8: NYC Traffic Volume Counts ve PLUTO veri kaynaklarını keşfetme.

Pilot bölge: Manhattan, Park Avenue.

Ne yapar:
  1. NYC Open Data'dan Automated Traffic Volume Counts (7ym2-wayt) verisinin
     Manhattan + Park Avenue kısmını ham CSV olarak indirir.
  2. PLUTO (64uk-42ks) verisinin Park Avenue'ya cephesi olan parsellerini indirir.
  3. Sayım noktası (SegmentID) sayısını, yıllarını ve kapsadığı kesitleri özetler.
  4. Jira yorumuna yapıştırılacak Markdown özetini yazar.

Çıktılar (varsayılan kök: ./auris-data):
  auris-data/demand/sources/atvc_park_ave_raw.csv
  auris-data/demand/sources/pluto_park_ave_raw.csv
  auris-data/demand/sources/scrum8_summary.md

Kurulum:  pip install requests pandas
Kullanım: python scrum8_explore.py [--data-dir auris-data] [--street "PARK AVENUE"]
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests

ATVC_URL = "https://data.cityofnewyork.us/resource/7ym2-wayt.csv"
PLUTO_URL = "https://data.cityofnewyork.us/resource/64uk-42ks.csv"
PAGE = 50_000


def fetch_all(url: str, where: str, select: str | None = None) -> pd.DataFrame:
    """Download every row matching `where` from a Socrata endpoint, page by page."""
    frames, offset = [], 0
    while True:
        params = {"$where": where, "$limit": PAGE, "$offset": offset, "$order": ":id"}
        if select:
            params["$select"] = select
        r = requests.get(url, params=params, timeout=180)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), low_memory=False)
        frames.append(df)
        print(f"  {url.rsplit('/', 1)[-1]}: {offset + len(df):,} satır", flush=True)
        if len(df) < PAGE:
            break
        offset += PAGE
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def summarize_atvc(df: pd.DataFrame) -> str:
    if df.empty:
        return "**Traffic Volume Counts:** Park Avenue için hiç kayıt bulunamadı.\n"
    df = df.copy()
    df["yr"] = pd.to_numeric(df["yr"], errors="coerce")
    df["date"] = pd.to_datetime(
        dict(year=df["yr"], month=pd.to_numeric(df["m"], errors="coerce"),
             day=pd.to_numeric(df["d"], errors="coerce")), errors="coerce")

    seg = (df.groupby("segmentid")
             .agg(kesit=("fromst", lambda s: f"{s.mode().iat[0]} → {df.loc[s.index, 'tost'].mode().iat[0]}"),
                  yillar=("yr", lambda s: ", ".join(str(int(y)) for y in sorted(s.dropna().unique()))),
                  gun=("date", "nunique"),
                  yon=("direction", lambda s: "/".join(sorted(s.dropna().astype(str).unique()))),
                  kayit=("vol", "size"))
             .reset_index()
             .sort_values("segmentid"))

    years = df.groupby("yr")["segmentid"].nunique().sort_index()
    lines = [
        "**Traffic Volume Counts (7ym2-wayt), Manhattan – Park Avenue**",
        f"- Sayım noktası (SegmentID): **{seg.shape[0]}**",
        f"- Toplam 15 dakikalık kayıt: {len(df):,}",
        f"- Tarih aralığı: {df['date'].min():%Y-%m-%d} – {df['date'].max():%Y-%m-%d}",
        "- Yıllara göre sayım noktası: " + ", ".join(f"{int(y)}: {n}" for y, n in years.items()),
        "",
        "| SegmentID | Kesit | Yıllar | Sayım günü | Yön |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {r.segmentid} | {r.kesit} | {r.yillar} | {r.gun} | {r.yon} |" for r in seg.itertuples()]
    return "\n".join(lines) + "\n"


def summarize_pluto(df: pd.DataFrame) -> str:
    if df.empty:
        return "**PLUTO:** Park Avenue adresli parsel bulunamadı.\n"
    n = len(df)
    def filled(col):  # share of non-empty values
        return f"{df[col].notna().mean():.0%}" if col in df else "kolon yok"
    lu = (df["landuse"].astype("Int64").value_counts().sort_index()
          if "landuse" in df else pd.Series(dtype=int))
    lu_names = {1: "1-2 aileli konut", 2: "Çok aileli konut (asansörsüz)", 3: "Çok aileli konut (asansörlü)",
                4: "Karma konut/ticari", 5: "Ticari/ofis", 6: "Sanayi", 7: "Ulaşım/altyapı",
                8: "Kamu/kurum", 9: "Açık alan", 10: "Otopark", 11: "Boş arsa"}
    lines = [
        "**PLUTO (64uk-42ks), Manhattan – Park Avenue adresli parseller**",
        f"- Parsel sayısı: **{n}**",
        f"- Doluluk: koordinat {filled('latitude')}, landuse {filled('landuse')}, "
        f"bldgarea {filled('bldgarea')}, officearea {filled('officearea')}, "
        f"resarea {filled('resarea')}, unitstotal {filled('unitstotal')}",
    ]
    if "bldgarea" in df:
        lines.append(f"- Toplam bina alanı: {pd.to_numeric(df['bldgarea'], errors='coerce').sum():,.0f} ft²")
    if not lu.empty:
        lines.append("- Arazi kullanımı: " + ", ".join(f"{lu_names.get(int(k), k)}: {v}" for k, v in lu.items()))
    if "version" in df:
        lines.append(f"- PLUTO sürümü: {df['version'].dropna().iloc[0]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="auris-data")
    ap.add_argument("--street", default="PARK AVENUE", help="Sokak adı (büyük harf, ATVC/PLUTO yazımı)")
    a = ap.parse_args()

    out = Path(a.data_dir) / "demand" / "sources"
    out.mkdir(parents=True, exist_ok=True)
    st = a.street.upper().replace("'", "''")

    print("1/2 Traffic Volume Counts indiriliyor...")
    atvc = fetch_all(ATVC_URL, f"boro = 'Manhattan' AND upper(street) = '{st}'")
    atvc.to_csv(out / "atvc_park_ave_raw.csv", index=False)

    print("2/2 PLUTO indiriliyor...")
    pluto = fetch_all(PLUTO_URL, f"borough = 'MN' AND upper(address) like '%{st}%'")
    pluto.to_csv(out / "pluto_park_ave_raw.csv", index=False)

    summary = (f"## SCRUM-8 sonuç: pilot bölge (Park Avenue) veri kontrolü\n\n"
               f"{summarize_atvc(atvc)}\n{summarize_pluto(pluto)}\n"
               f"Ham dosyalar: `auris-data/demand/sources/` (atvc_park_ave_raw.csv, pluto_park_ave_raw.csv)\n")
    (out / "scrum8_summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)
    print(f"Özet yazıldı: {out / 'scrum8_summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())