
from pathlib import Path
from datetime import datetime
import csv, re, time, sys, json
import requests
from bs4 import BeautifulSoup
import yaml
from urllib.parse import urlparse, urljoin

USER_AGENT = "FitGroundBot/1.0 (+https://github.com/FitGround)"
REQUEST_TIMEOUT = 25
REQUEST_GAP_SEC = 1.0

MARGINS = {"tent":1.10,"shelter":1.15,"tarp":1.20}

def to_m(val):
    if val is None: return ""
    s = str(val).strip().lower().replace('″','"').replace('’',"'")
    nums = re.findall(r"[0-9]+(?:\.[0-9]+)?", s)
    if not nums:
        try: return float(s)
        except: return ""
    n = float(nums[0])
    if "cm" in s:  return round(n/100.0, 3)
    if "mm" in s:  return round(n/1000.0, 3)
    if "ft" in s:  return round(n*0.3048, 3)
    if '"' in s or "inch" in s or "in " in s: return round(n*0.0254, 3)
    return round(n, 3)

def area_m2(w, d):
    try: return round(float(w) * float(d), 4)
    except: return ""

def with_margin(x, ratio):
    try: return round(float(x) * float(ratio), 3)
    except: return ""

def parse_width_depth(text):
    if not text: return ("","")
    s = str(text).replace("×","x").replace("X","x").replace("*","x")
    s = re.sub(r"[whd]\s*", "", s, flags=re.I)
    nums = re.findall(r"([0-9]+(?:\.[0-9]+)?)", s)
    unit = "m"
    if "cm" in s: unit="cm"
    elif "mm" in s: unit="mm"
    elif "ft" in s: unit="ft"
    elif '"' in s or "inch" in s or "in " in s: unit="inch"
    if len(nums) >= 2:
        w = to_m(nums[0] + unit)
        d = to_m(nums[1] + unit)
        return (w, d)
    return ("","")

def load_targets(path="brands.yaml"):
    with open(path,"r",encoding="utf-8") as f:
        y = yaml.safe_load(f)
    return y.get("brands", [])

def same_host(a, b):
    return urlparse(a).netloc == urlparse(b).netloc

def discover_links(b, session):
    base = b.get("base_url","").strip()
    if not base:
        return []
    allow_paths = b.get("allow_paths", [])
    import re as _re
    patt = _re.compile(b.get("product_link_pattern", "/product/"))
    limits = b.get("limits", {})
    max_pages = int(limits.get("max_pages", 200))
    max_depth = int(limits.get("max_depth", 3))

    seen, products = set(), set()
    from collections import deque
    q = deque([(base,0)])

    # sitemap 우선
    sm = b.get("sitemap_url","").strip()
    if sm:
        try:
            r = session.get(sm, timeout=REQUEST_TIMEOUT)
            if r.ok:
                soup = BeautifulSoup(r.text, "xml")
                for loc in soup.find_all("loc"):
                    u = loc.text.strip()
                    if same_host(u, base) and patt.search(u):
                        products.add(u)
        except Exception:
            pass

    while q and len(seen) < max_pages:
        url, depth = q.popleft()
        if url in seen or depth > max_depth: continue
        seen.add(url)
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except Exception:
            continue
        doc = BeautifulSoup(r.text, "lxml")
        for a in doc.select("a[href]"):
            href = a.get("href")
            if not href: continue
            link = urljoin(url, href)
            if not same_host(link, base): continue
            path = urlparse(link).path or "/"
            if allow_paths and not any(path.startswith(p) for p in allow_paths):
                continue
            if patt.search(link):
                products.add(link)
            if link not in seen:
                q.append((link, depth+1))
        time.sleep(REQUEST_GAP_SEC)
    return sorted(products)

def scrape_product_page(url, sel, category, brand, brand_ko, session):
    r = session.get(url, timeout=REQUEST_TIMEOUT); r.raise_for_status()
    doc = BeautifulSoup(r.text, "lxml")
    def tx(q):
        if not q: return ""
        el = doc.select_one(q)
        return el.get_text(strip=True) if el else ""
    name_ko = tx(sel.get("name_ko"))
    name_en = tx(sel.get("name_en"))
    size_txt = tx(sel.get("size"))
    w, d = parse_width_depth(size_txt)
    margin = MARGINS.get(category, 1.10)
    return {
        "brand": brand, "brand_ko": brand_ko, "category": category,
        "product_name_ko": name_ko, "product_name_en": name_en,
        "size_width_m": w, "size_depth_m": d, "area_m2": area_m2(w, d),
        "min_site_width_m": with_margin(w, margin),
        "min_site_depth_m": with_margin(d, margin),
        "min_site_area_m2": area_m2(with_margin(w, margin), with_margin(d, margin)),
    }

def write_outputs(rows):
    out_dir = Path("brand_outputs"); out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    snap = out_dir / f"tents_{ts}.csv"
    latest = out_dir / "latest.csv"
    cols = ["brand","brand_ko","category","product_name_ko","product_name_en","size_width_m","size_depth_m","area_m2","min_site_width_m","min_site_depth_m","min_site_area_m2"]
    def dump(path):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
            for r in rows: w.writerow({k:r.get(k,"") for k in cols})
    dump(snap); dump(latest)
    print(f"Saved snapshot: {snap}")
    print(f"Updated latest: {latest}")

def main():
    targets = load_targets()
    session = requests.Session(); session.headers.update({"User-Agent": USER_AGENT})
    all_rows = []
    for b in targets:
        key = b.get("key","")
        brand = b.get("brand",""); brand_ko = b.get("brand_ko",""); cat = b.get("category","tent")
        products = discover_links(b, session)
        Path("brand_outputs").mkdir(exist_ok=True)
        with open(f"brand_outputs/discovered_urls_{key or 'brand'}.json","w",encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        for u in products:
            try:
                row = scrape_product_page(u, b.get("selectors",{}), cat, brand, brand_ko, session)
                if any([row["product_name_ko"], row["product_name_en"], row["size_width_m"]]):
                    all_rows.append(row)
            except Exception as e:
                print(f"[WARN] {key} fail: {u} :: {e}", file=sys.stderr)
    seen=set(); dedup=[]
    for r in all_rows:
        k=(r.get("brand",""),r.get("product_name_ko",""),r.get("product_name_en",""))
        if k in seen: continue
        seen.add(k); dedup.append(r)
    write_outputs(dedup)

if __name__ == "__main__":
    main()
