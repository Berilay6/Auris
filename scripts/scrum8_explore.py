"""SCRUM-8: NYC Traffic Volume Counts ve PLUTO veri kaynaklarını keşfetme.

Pilot bölge sınırı config/pilot_region.yaml dosyasından okunur (projede tek kaynak;
bootstrap_network.py de aynı dosyayı kullanır). Poligon ve buffer_m oradan gelir.

Ne yapar:
  1. Manhattan'daki tüm ATVC sayım noktalarının konumunu çeker, pilot poligona
     düşenleri seçer, sonra yalnızca bu noktaların ham kayıtlarını indirir.
  2. PLUTO'dan pilot poligona düşen parselleri indirir.
  3. Sayım noktası sayısını, yıllarını, gün sayısını özetler; PLUTO doluluğunu verir.
  4. Jira yorumuna yapıştırılacak Markdown özetini yazar.

Tüm geometri NY State Plane (EPSG:2263, feet) üzerinde hesaplanır; ATVC (WktGeom)
ve PLUTO (xcoord/ycoord) zaten bu sistemde.

Çıktılar (varsayılan kök: ./auris-data — betiği depo kökünden çalıştırın):
  auris-data/demand/sources/atvc_pilot_raw.csv
  auris-data/demand/sources/pluto_pilot_raw.csv
  auris-data/demand/sources/scrum8_summary.md

Kurulum:  py -m pip install requests pandas pyproj pyyaml
Kullanım: py scripts/scrum8_explore.py [--config config/pilot_region.yaml] [--data-dir auris-data]
"""
from __future__ import annotations

import argparse
import io
import math
import re
import sys
from pathlib import Path

import pandas as pd
import requests
import yaml
from pyproj import Transformer

ATVC_URL = "https://data.cityofnewyork.us/resource/7ym2-wayt.csv"
PLUTO_URL = "https://data.cityofnewyork.us/resource/64uk-42ks.csv"
PAGE = 50_000

FT_PER_M = 3.28084


def load_region(path: Path) -> tuple[str, list[tuple[float, float]], float]:
    """Read name, polygon (EPSG:2263 feet) and buffer (m) from pilot_region.yaml."""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))["region"]
    b = cfg["boundary"]
    if b["type"] == "polygon":
        ring = [tuple(p) for p in b["polygon"]]          # [lon, lat]
        if ring[0] == ring[-1]:
            ring = ring[:-1]
    elif b["type"] == "bbox":
        w, s_, e, n = (b["bbox"][k] for k in ("west", "south", "east", "north"))
        ring = [(w, s_), (e, s_), (e, n), (w, n)]
    else:
        raise ValueError(f"Bilinmeyen boundary.type: {b['type']}")
    tr = Transformer.from_crs("EPSG:4326", "EPSG:2263", always_xy=True)
    return cfg.get("name", cfg.get("id", "pilot")), [tr.transform(lon, lat) for lon, lat in ring], \
        float(b.get("buffer_m", 0) or 0)


def _inside(x: float, y: float, poly) -> bool:
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def _edge_dist(x: float, y: float, poly) -> float:
    best = math.inf
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def in_pilot(x: float, y: float, poly, buffer_ft: float) -> bool:
    if pd.isna(x) or pd.isna(y):
        return False
    return _inside(x, y, poly) or _edge_dist(x, y, poly) <= buffer_ft


def fetch_all(url: str, params: dict) -> pd.DataFrame:
    """Download every row from a Socrata endpoint, page by page."""
    frames, offset = [], 0
    while True:
        p = {**params, "$limit": PAGE, "$offset": offset}
        r = requests.get(url, params=p, timeout=300)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), low_memory=False)
        frames.append(df)
        print(f"  {url.rsplit('/', 1)[-1]}: {offset + len(df):,} satır", flush=True)
        if len(df) < PAGE:
            break
        offset += PAGE
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


POINT_RE = re.compile(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", re.I)


def parse_point(wkt: str) -> tuple[float, float]:
    m = POINT_RE.search(str(wkt))
    return (float(m.group(1)), float(m.group(2))) if m else (math.nan, math.nan)


def summarize_atvc(df: pd.DataFrame) -> str:
    if df.empty:
        return "**Traffic Volume Counts:** Pilot bölgede hiç kayıt bulunamadı.\n"
    df = df.copy()
    df["yr"] = pd.to_numeric(df["yr"], errors="coerce")
    df["date"] = pd.to_datetime(
        dict(year=df["yr"], month=pd.to_numeric(df["m"], errors="coerce"),
             day=pd.to_numeric(df["d"], errors="coerce")), errors="coerce")

    def mode(s):
        s = s.dropna()
        return s.mode().iat[0] if not s.empty else "?"

    seg = (df.groupby("segmentid")
             .agg(street=("street", mode), fromst=("fromst", mode), tost=("tost", mode),
                  yillar=("yr", lambda s: ", ".join(str(int(y)) for y in sorted(s.dropna().unique()))),
                  gun=("date", "nunique"), son=("date", "max"),
                  yon=("direction", lambda s: "/".join(sorted(s.dropna().astype(str).unique()))))
             .reset_index()
             .sort_values(["street", "segmentid"]))

    days = df.drop_duplicates(["segmentid", "date"])
    years = df.groupby("yr")["segmentid"].nunique().sort_index()
    recent = days[days["date"] >= "2025-01-05"]  # congestion pricing start
    lines = [
        "**Traffic Volume Counts (7ym2-wayt), pilot poligon**",
        f"- Sayım noktası (SegmentID): **{seg.shape[0]}**",
        f"- Sayım günü (nokta × gün): {len(days):,}",
        f"- Toplam 15 dakikalık kayıt: {len(df):,}",
        f"- Tarih aralığı: {df['date'].min():%Y-%m-%d} – {df['date'].max():%Y-%m-%d}",
        f"- Congestion pricing sonrası (5 Oca 2025+): {recent['segmentid'].nunique()} nokta, "
        f"{recent['date'].nunique()} farklı gün",
        "- Yıllara göre sayım noktası: " + ", ".join(f"{int(y)}: {n}" for y, n in years.items()),
        "",
        "| SegmentID | Cadde | Kesit | Yıllar | Sayım günü | Son sayım | Yön |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [f"| {r.segmentid} | {r.street} | {r.fromst} → {r.tost} | {r.yillar} | {r.gun} | "
              f"{r.son:%Y-%m-%d} | {r.yon} |" for r in seg.itertuples()]
    return "\n".join(lines) + "\n"


def summarize_pluto(df: pd.DataFrame) -> str:
    if df.empty:
        return "**PLUTO:** Pilot bölgede parsel bulunamadı.\n"
    n = len(df)

    def filled(col):
        return f"{df[col].notna().mean():.0%}" if col in df else "kolon yok"

    lu_names = {1: "1-2 aileli konut", 2: "Çok aileli (asansörsüz)", 3: "Çok aileli (asansörlü)",
                4: "Karma konut/ticari", 5: "Ticari/ofis", 6: "Sanayi", 7: "Ulaşım/altyapı",
                8: "Kamu/kurum", 9: "Açık alan", 10: "Otopark", 11: "Boş arsa"}
    num = lambda c: pd.to_numeric(df[c], errors="coerce").sum() if c in df else float("nan")
    lines = [
        "**PLUTO (64uk-42ks), pilot poligondaki parseller**",
        f"- Parsel sayısı: **{n}**",
        f"- Doluluk: landuse {filled('landuse')}, bldgarea {filled('bldgarea')}, "
        f"officearea {filled('officearea')}, resarea {filled('resarea')}, "
        f"retailarea {filled('retailarea')}, unitstotal {filled('unitstotal')}",
        f"- Toplam bina alanı: {num('bldgarea'):,.0f} ft² · ofis {num('officearea'):,.0f} ft² · "
        f"konut {num('resarea'):,.0f} ft² · perakende {num('retailarea'):,.0f} ft²",
        f"- Toplam konut birimi: {num('unitsres'):,.0f}",
    ]
    if "landuse" in df:
        lu = df["landuse"].astype("Int64").value_counts().sort_values(ascending=False)
        lines.append("- Arazi kullanımı: " + ", ".join(f"{lu_names.get(int(k), k)}: {v}" for k, v in lu.items()))
    if "version" in df:
        lines.append(f"- PLUTO sürümü: {df['version'].dropna().iloc[0]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="auris-data")
    ap.add_argument("--config", default="config/pilot_region.yaml")
    a = ap.parse_args()

    out = Path(a.data_dir) / "demand" / "sources"
    out.mkdir(parents=True, exist_ok=True)
    name, poly, buffer_m = load_region(Path(a.config))
    buf = buffer_m * FT_PER_M
    print(f"Pilot bölge: {name} · {len(poly)} köşe · buffer {buffer_m:g} m")
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    pad = buf + 100

    print("1/3 Manhattan sayım noktalarının konumu çekiliyor...")
    locs = fetch_all(ATVC_URL, {"$select": "segmentid, wktgeom", "$group": "segmentid, wktgeom",
                                "$where": "boro = 'Manhattan'", "$order": "segmentid"})
    locs[["x", "y"]] = locs["wktgeom"].apply(lambda w: pd.Series(parse_point(w)))
    seg_ids = sorted(locs.loc[[in_pilot(x, y, poly, buf) for x, y in zip(locs.x, locs.y)],
                              "segmentid"].astype(int).unique())
    print(f"  Pilot poligonda {len(seg_ids)} sayım noktası: {seg_ids}")

    print("2/3 Bu noktaların ham sayımları indiriliyor...")
    if seg_ids:
        atvc = fetch_all(ATVC_URL, {"$where": f"segmentid in ({', '.join(map(str, seg_ids))})",
                                    "$order": ":id"})
    else:
        atvc = pd.DataFrame()
    atvc.to_csv(out / "atvc_pilot_raw.csv", index=False)

    print("3/3 PLUTO indiriliyor...")
    pluto = fetch_all(PLUTO_URL, {"$where": (f"borough = 'MN' AND xcoord between {min(xs) - pad:.0f} "
                                             f"and {max(xs) + pad:.0f} AND ycoord between "
                                             f"{min(ys) - pad:.0f} and {max(ys) + pad:.0f}"),
                                  "$order": "bbl"})
    if not pluto.empty:
        px, py = pd.to_numeric(pluto["xcoord"], errors="coerce"), pd.to_numeric(pluto["ycoord"], errors="coerce")
        pluto = pluto[[in_pilot(x, y, poly, buf) for x, y in zip(px, py)]]
    pluto.to_csv(out / "pluto_pilot_raw.csv", index=False)

    summary = (
        "## SCRUM-8 sonuç: pilot bölge veri kontrolü\n\n"
        f"Pilot bölge: {name} (`{a.config}`, buffer {buffer_m:g} m; sayım noktaları ve PLUTO parselleri "
        "aynı genişletilmiş sınırla seçildi)\n\n"
        f"{summarize_atvc(atvc)}\n{summarize_pluto(pluto)}\n"
        "Ham dosyalar: `auris-data/demand/sources/` (atvc_pilot_raw.csv, pluto_pilot_raw.csv)\n"
    )
    (out / "scrum8_summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)
    print(f"Özet yazıldı: {out / 'scrum8_summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
