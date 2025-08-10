
import csv, json, re, time
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

UA = "FitGroundBot/1.0 (+https://github.com/FitGround)"
TIMEOUT = 20
GAP = 1.0

EXCLUDE_HOSTS = [
    "amazon.", "ebay.", "rakuten.", "smartstore.naver", "coupang.",
    "instagram.", "facebook.", "x.com", "twitter.", "youtube.", "tiktok."
]

def normalize(u):
    if not u: return ""
    if not u.startswith("http"):
        u = "https://" + u.lstrip("/")
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}/"

def fetch(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        return r
    except Exception:
        return None

def ddg_search(brand):
    url = "https://duckduckgo.com/html/?q=" + requests.utils.quote(brand + " official site")
    r = fetch(url)
    if not r: return []
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for a in soup.select("a.result__a"):
        href = a.get("href")
        if href: out.append(href)
    return out[:5]

def looks_official(host, brand):
    h = host.lower()
    b = re.sub(r"[^a-z0-9]","", brand.lower())
    if b and b in h:
        if not any(ex in h for ex in EXCLUDE_HOSTS):
            return True
    return False

def resolve_one(brand):
    cands = []
    for u in ddg_search(brand):
        try:
            cands.append(normalize(u))
        except: pass
    scored=[]
    for u in cands:
        host = urlparse(u).netloc.lower()
        if any(ex in host for ex in EXCLUDE_HOSTS): continue
        score = 0
        if looks_official(host, brand): score += 5
        r = fetch(u); time.sleep(GAP)
        if r:
            s = BeautifulSoup(r.text, "lxml")
            if s.select('a[href*="product"], a[href*="shop"], a[href*="store"]'): score += 1
            if fetch(u + "sitemap.xml"): score += 1
        scored.append((score,u))
    scored.sort(reverse=True)
    return scored[0][1] if scored else ""

def main():
    inp = Path("brands/brands.csv")
    out = Path("brands/brand_domains.json")
    out.parent.mkdir(exist_ok=True, parents=True)
    domains = {}
    with inp.open(encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            brand = row.get("brand","").strip()
            if not brand: continue
            print(f"[resolve] {brand} ...")
            base = resolve_one(brand)
            domains[brand] = base
            print(" =>", base)
    out.write_text(json.dumps(domains, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
