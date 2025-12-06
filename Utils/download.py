import csv
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import time
import random
import pandas as pd  # Để xuất Excel (pip install pandas openpyxl)

# ====================== CẤU HÌNH ======================
CSV_FILE = "products-0-200000.csv"  # File CSV của bạn (200k IDs)
ID_COLUMN = "id"  # Tên cột chứa ID

BASE_URL = "https://api.tiki.vn/product-detail/api/v1/products/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://tiki.vn/",
    "Origin": "https://tiki.vn",  # Bắt buộc để tránh block
    "Connection": "keep-alive",
}

MAX_WORKERS = 20  # 20-30 để tránh rate limit (Tiki chịu tốt ~20-30 req/s)
RETRY_COUNT = 2  # Thử lại nếu lỗi
ADD_DELAY = True  # Delay ngẫu nhiên 0.1-0.3s để giống người thật


# =====================================================
# Read ids then parse into
def read_ids_from_csv(file_path, column_name="id"):
    """Đọc ID từ CSV, loại trùng, hỗ trợ URL"""
    if not os.path.exists(file_path):
        print(f"Không tìm thấy file: {file_path}")
        return []

    ids = set()  # Loại trùng
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            id_val = row.get(column_name) or row.get(column_name.lower()) or row.get(column_name.upper())
            id_val = str(id_val).strip()
            if id_val.isdigit():
                ids.add(int(id_val))
            elif "tiki.vn" in id_val and "-p" in id_val:
                try:
                    product_id = id_val.split("-p")[-1].split(".")[0].split("?")[0]
                    if product_id.isdigit():
                        ids.add(int(product_id))
                except:
                    continue
    ids = list(ids)
    print(f"Đã đọc {len(ids)} ID hợp lệ (duy nhất) từ file '{file_path}'")
    return ids


def fetch_product(product_id):
    """Lấy chi tiết 1 sản phẩm (single ID)"""
    url = f"{BASE_URL}{product_id}"
    for attempt in range(RETRY_COUNT + 1):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data and "id" in data:  # Kiểm tra dữ liệu hợp lệ
                    if ADD_DELAY:
                        time.sleep(random.uniform(0.1, 0.3))
                    return data
                else:
                    print(f"Data rỗng cho ID {product_id}")
                    return None
            elif r.status_code == 404:
                print(f"ID {product_id} không tồn tại (404)")
                return None
            elif r.status_code == 429:
                print(f"Rate limit! Chờ 5s cho ID {product_id}...")
                time.sleep(5)
                continue
            else:
                print(f"HTTP {r.status_code} cho ID {product_id}")
        except Exception as e:
            if attempt < RETRY_COUNT:
                time.sleep(2)
                continue
            print(f"Lỗi với ID {product_id}: {e}")
    return None


# =================== CHẠY CHÍNH =====================
print("Bắt đầu crawl dữ liệu sản phẩm Tiki từ file CSV...\n")

product_ids = read_ids_from_csv(CSV_FILE, ID_COLUMN)
if not product_ids:
    print("Không có ID nào để xử lý. Dừng lại.")
    exit()

print(f"Dùng {MAX_WORKERS} luồng để tăng tốc...\n")

all_products = []
failed_ids = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_id = {executor.submit(fetch_product, pid): pid for pid in product_ids}

    for future in as_completed(future_to_id):
        pid = future_to_id[future]
        try:
            product = future.result()
            if product:
                all_products.append(product)
                name = product.get('name', 'Không tên')[:50]
                print(f"✓ Đã lấy ID {pid}: {name}...")
            else:
                failed_ids.append(pid)
        except Exception as e:
            failed_ids.append(pid)
            print(f"✗ Lỗi nghiêm trọng ID {pid}: {e}")

# =================== KẾT QUẢ ========================
print(f"\nHOÀN TẤT!")
print(f"Tổng sản phẩm lấy thành công: {len(all_products)} / {len(product_ids)}")

# In thử 5 sản phẩm đầu
for i, p in enumerate(all_products[:5]):
    name = p.get('name', 'Không có tên')
    price = p.get('price')
    price_str = f"{price:,} ₫" if price else "Liên hệ"
    print(f"{i + 1}. [{p['id']}] {name[:70]}{'...' if len(name) > 70 else ''} → {price_str}")

# Lưu JSON đầy đủ
output_json = "tiki_products_result.json"
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(all_products, f, ensure_ascii=False, indent=2)
print(f"\nĐã lưu JSON đầy đủ vào: {output_json}")

# Lưu Excel dễ đọc (cột chính)
if all_products:
    df = pd.DataFrame(all_products)
    # Chỉ giữ cột quan trọng để file không nặng
    columns_to_keep = ['id', 'name', 'sku', 'price', 'original_price', 'discount', 'rating_average', 'review_count',
                       'inventory_status', 'short_description']
    df = df[columns_to_keep]
    output_excel = "tiki_products_result.xlsx"
    df.to_excel(output_excel, index=False)
    print(f"Đã lưu Excel (cột chính) vào: {output_excel}")

# Lưu ID lỗi
if failed_ids:
    with open("failed_ids.txt", "w") as f:
        f.write("\n".join(map(str, failed_ids)))
    print(f"{len(failed_ids)} ID lỗi đã lưu vào failed_ids.txt (chạy lại bằng cách copy vào CSV mới)")

print("\nHoàn thành! Nếu bị block, giảm MAX_WORKERS xuống 10-15 và thử lại.")