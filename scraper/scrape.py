from pathlib import Path
from datetime import datetime
import csv, re, math, json, sys

# --- FitGround 규격 헬퍼 ---
def to_m(val):
    # 문자열/숫자를 미터로 변환 (cm, mm, m, ft, inch 일부 처리)
    if val is None or str(val).strip() == "":
        return ""
    s = str(val).strip().lower().replace('″','"').replace('’',"'")
    # 패턴 예시: "300x250 cm" / "3m x 2.5m" / "9.8ft x 7.2ft"
    num = re.findall(r"[0-9]+(?:\.[0-9]+)?", s)
    if not num:
        try:
            return float(s)
        except:
            return ""
    # 단위 판단
    if "cm" in s:
        return float(num[0]) / 100.0
    if "mm" in s:
        return float(num[0]) / 1000.0
    if "ft" in s or "foot" in s:
        return float(num[0]) * 0.3048
    if '"' in s or "inch" in s or "in " in s:
        return float(num[0]) * 0.0254
    # 기본 m 가정
    return float(num[0])

def area_m2(w, d):
    try:
        return round(float(w) * float(d), 4)
    except:
        return ""

def apply_margin(value, ratio):
    try:
        return round(float(value) * float(ratio), 3)
    except:
        return ""

# 카테고리별 여유계수(예시값) — 필요 시 조정
MARGINS = {
    "tent": 1.1,
    "shelter": 1.15,
    "tarp": 1.2,
}

# --- 출력 초기화 ---
out_dir = Path("brand_outputs")
out_dir.mkdir(parents=True, exist_ok=True)
ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
snapshot_csv = out_dir / f"tents_{ts}.csv"
latest_csv = out_dir / "latest.csv"

# --- 여기에 실제 수집 로직 추가 ---
# 지금은 샘플 한 줄만 출력
rows = [
    {
        "brand": "SAMPLE BRAND",
        "brand_ko": "샘플브랜드",
        "category": "tent",
        "product_name_ko": "샘플텐트",
        "product_name_en": "Sample Tent",
        "size_width_m": 3.0,
        "size_depth_m": 2.5,
    }
]

# 후처리(면적/최소 설치면적)
for r in rows:
    w = to_m(r.get("size_width_m", ""))
    d = to_m(r.get("size_depth_m", ""))
    r["size_width_m"] = w
    r["size_depth_m"] = d
    r["area_m2"] = area_m2(w, d)
    margin = MARGINS.get(r.get("category","tent"), 1.1)
    r["min_site_width_m"]  = apply_margin(w, margin)
    r["min_site_depth_m"]  = apply_margin(d, margin)
    r["min_site_area_m2"]  = area_m2(r["min_site_width_m"], r["min_site_depth_m"])

# CSV 컬럼
fieldnames = [
    "brand", "brand_ko", "category",
    "product_name_ko", "product_name_en",
    "size_width_m", "size_depth_m", "area_m2",
    "min_site_width_m", "min_site_depth_m", "min_site_area_m2"
]

def write_csv(path):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

write_csv(snapshot_csv)
write_csv(latest_csv)

print(f"Saved snapshot: {snapshot_csv}")
print(f"Updated latest: {latest_csv}")
