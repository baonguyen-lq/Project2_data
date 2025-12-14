import json
import re
from .config import CONFIG

TIKI_FOOTER = CONFIG['cleaner']['tiki_footer']

def clean_html(raw_html):
    if not raw_html:
        return ""
    text = raw_html.split(TIKI_FOOTER)[0]
    clean_text = re.sub(r'<.*?>', '', text)
    clean_text = re.sub(r'<br\s*/?>', '\n', clean_text)
    lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
    clean_text = "\n".join(lines)
    clean_text = re.sub(r'[^\w\s\.,:;()\-%/]', '', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    clean_text = clean_text.strip()
    return clean_text

def extract_info(text):
    info = {"origin": "", "material": "", "warranty": "", "brand": ""}
    t = text.lower()
    m = re.search(r'(?:xuất xứ|xuất sứ|nước sản xuất|origin)[:\s]*(.*?)(?:\n|$|,|.)', t)
    if m:
        o = m.group(1).strip()
        o = re.sub(r'(vietnam|vn|việt nam)', 'Việt Nam', o, flags=re.I)
        o = re.sub(r'(trung quốc|china|tq)', 'Trung Quốc', o, flags=re.I)
        info["origin"] = o.title()
    m = re.search(r'chất liệu[:\s]*(.*?)(?:\n|$|,|.)', t)
    if m: info["material"] = m.group(1).strip().title()
    m = re.search(r'bảo hành[:\s]*(\d+\s*(?:tháng|năm)|trọn đời)', t)
    if m: info["warranty"] = m.group(1).strip().title()
    for pat in [r'thương hiệu[:\s]*([^\n,<]+)', r'brand[:\s]*([^\n,<]+)']:
        m = re.search(pat, t)
        if m:
            info["brand"] = m.group(1).strip().title()
            break
    return info

# Hàm clean chính (gọi từ script)
def run_cleaner(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    cleaned = []
    for p in products:
        desc = clean_html(p.get("description", ""))
        info = extract_info(desc)
        cleaned.append({
            "id": p.get("id"),
            "name": p.get("name", "").strip(),
            "url_key": p.get("url_key"),
            "price": p.get("price"),
            "description": desc,
            "images_count": len(p.get("images", [])),
            "origin": info["origin"],
            "material": info["material"],
            "warranty": info["warranty"],
            "brand_from_desc": info["brand"]
        })
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)