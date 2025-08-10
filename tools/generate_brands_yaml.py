
import csv, json, yaml
from pathlib import Path
DEFAULT = {
  "category": "tent",
  "allow_paths": [],  # ← 빈 리스트로
  "product_link_pattern": "(product|goods|detail|item|shop|store|view|catalog|collection)",
  "limits": {"max_pages": 200, "max_depth": 3},
  "selectors": {
    "name_ko": "h1, .product-title, .title",
    "name_en": "",
    "size": ".spec, .size, .dimension, .dimensions"
  }
}
def slug(s):
    import re
    return re.sub(r"[^a-z0-9]+","-", (s or "").lower()).strip("-")
def main():
    brands_csv = Path("brands/brands.csv")
    domains_json = Path("brands/brand_domains.json")
    out_yaml = Path("brands.yaml")
    rows = list(csv.DictReader(brands_csv.open(encoding="utf-8")))
    domains = json.loads(domains_json.read_text(encoding="utf-8")) if domains_json.exists() else {}
    out = {"brands": []}
    for r in rows:
        ko = (r.get("brand_ko","") or "").strip()
        en = (r.get("brand","") or "").strip()
        key = slug(en or ko)
        base = domains.get(en, "")
        item = {
            "key": key, "brand_ko": ko, "brand": en, "category": DEFAULT["category"],
            "base_url": base or "", "sitemap_url": (base + "sitemap.xml") if base else "",
            "allow_paths": DEFAULT["allow_paths"],
            "product_link_pattern": DEFAULT["product_link_pattern"],
            "limits": DEFAULT["limits"],
            "selectors": DEFAULT["selectors"],
        }
        out["brands"].append(item)
    with out_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False)
    print(f"Saved: {out_yaml}")
if __name__ == "__main__":
    main()
