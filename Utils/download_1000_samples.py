
from typing import List

import csv
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import time
import random
import pandas as pd  # Để xuất Excel (pip install pandas openpyxl nếu chưa có)

# ====================== CẤU HÌNH ======================
CSV_FILE = "products-0-200000.csv"
ID_COLUMN = "id"

BASE_URL = "https://api.tiki.vn/product-detail/api/v1/products/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://tiki.vn/",
    "Origin": "https://tiki.vn",
    "Connection": "keep-alive",
}

# Fields muốn lấy từ mỗi sản phẩm
FIELDS = ['id', 'name', 'url_key', 'price', 'description', 'images']
MAX_WORKERS = 20  # 20-30 để tránh rate limit (Tiki chịu tốt ~20-30 req/s)
RETRY_COUNT = 3  # Thử lại từng ID tối đa 3 lần nếu lỗi
MAX_RETRY_ROUNDS = 5  # Số vòng retry toàn bộ failed IDs (để đảm bảo lấy đủ)
ADD_DELAY = True  # Delay ngẫu nhiên 0.1-0.5s để giống người thật, tránh block

# =====================================================
# Read 1000 samples from file_path
def read_ids_from_csv(file_path: str, column_name: str = "id", max_samples: int = 1000, unique: bool = True) -> List[int]:
    """
    Read up to max_samples IDs from CSV in file order.
    - column_name: header to look for (case-insensitive).
    - max_samples: stop after collecting this many valid IDs.
    - unique: if True, return unique IDs (first occurrence kept); if False, allow duplicates.
    """
    if not os.path.exists(file_path):
        print(f"Can not find file: {file_path}")
        return []

    ids_list = []
    seen = set() if unique else None

    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # stop when reached required number of samples
            if len(ids_list) >= max_samples:
                break

            id_val = row.get(column_name) or row.get(column_name.lower()) or row.get(column_name.upper())
            if id_val is None:
                continue
            id_val = str(id_val).strip()

            # direct numeric id
            if id_val.isdigit():
                candidate = int(id_val)
            # tiki.vn product url pattern
            elif "tiki.vn" in id_val and "-p" in id_val:
                try:
                    product_id = id_val.split("-p")[-1].split(".")[0].split("?")[0]
                    if product_id.isdigit():
                        candidate = int(product_id)
                    else:
                        continue
                except Exception:
                    continue
            else:
                continue

            if unique:
                if candidate in seen:
                    continue
                seen.add(candidate)
            ids_list.append(candidate)

    print(f"Đã đọc {len(ids_list)} ID hợp lệ (the first {max_samples} samples, unique={unique}) từ file '{file_path}'")
    return ids_list

def fetch_product(product_id):
    """Lấy chi tiết 1 sản phẩm (single ID) và extract fields cần thiết"""
    url = f"{BASE_URL}{product_id}"
    for attempt in range(RETRY_COUNT + 1):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data and data.get('id') == product_id:  # Kiểm tra ID đúng để đảm bảo thông tin chính xác
                    # Extract fields cần thiết
                    product = {
                        'id': data.get('id'),
                        'name': data.get('name'),
                        'url_key': data.get('url_key'),
                        'price': data.get('price'),
                        'description': data.get('description') or data.get('short_description', ''),
                        # Ưu tiên description đầy đủ
                        'images': [img.get('large_url') or img.get('base_url', '') for img in data.get('images', [])]
                        # List URLs ảnh
                    }
                    if ADD_DELAY:
                        time.sleep(random.uniform(0.1, 0.5))  # Delay ngẫu nhiên
                    return product
                else:
                    print(f"Data rỗng hoặc ID không khớp cho {product_id}")
                    return None
            elif r.status_code == 404:
                print(f"ID {product_id} không tồn tại (404) - Bỏ qua vĩnh viễn")
                return None
            elif r.status_code == 429:
                print(f"Rate limit! Chờ 10s cho ID {product_id}...")
                time.sleep(10)
                continue
            else:
                print(f"HTTP {r.status_code} cho ID {product_id}")
        except Exception as e:
            if attempt < RETRY_COUNT:
                time.sleep(3)  # Chờ lâu hơn nếu lỗi mạng
                continue
            print(f"Lỗi cuối cùng với ID {product_id}: {e}")
    return None
# =================== CHẠY CHÍNH =====================
print("Bắt đầu crawl dữ liệu sản phẩm Tiki từ file CSV...\n")

# Đọc ID ban đầu
all_ids = read_ids_from_csv(CSV_FILE, ID_COLUMN)
if not all_ids:
    print("Không có ID nào để xử lý. Dừng lại.")
    exit()

total_target = len(all_ids)  # Mục tiêu: lấy đủ số này (200k)
all_products = []  # List sản phẩm thành công
failed_ids = all_ids.copy()  # Bắt đầu với tất cả ID là "failed" để retry loop

# Loop retry toàn bộ failed IDs đến khi hết hoặc đạt max rounds
for round_num in range(1, MAX_RETRY_ROUNDS + 1):
    if not failed_ids:
        break  # Đã lấy hết

    print(f"\nVòng retry {round_num}/{MAX_RETRY_ROUNDS} - Còn {len(failed_ids)} ID cần lấy...\n")

    current_failed = []  # Failed của vòng này

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {executor.submit(fetch_product, pid): pid for pid in failed_ids}

        for future in as_completed(future_to_id):
            pid = future_to_id[future]
            try:
                product = future.result()
                if product:
                    all_products.append(product)
                    print(f"✓ Đã lấy ID {pid}: {product['name'][:50]}...")
                else:
                    current_failed.append(pid)
            except Exception as e:
                current_failed.append(pid)
                print(f"✗ Lỗi nghiêm trọng ID {pid}: {e}")

    failed_ids = current_failed  # Cập nhật failed cho vòng sau

    # Lưu failed tạm thời sau mỗi vòng
    if failed_ids:
        with open(f"failed_ids_round_{round_num}.txt", "w") as f:
            f.write("\n".join(map(str, failed_ids)))
        print(f"Đã lưu {len(failed_ids)} ID failed tạm thời vào failed_ids_round_{round_num}.txt")
# =================== KẾT QUẢ ========================
print(f"\nHOÀN TẤT SAU {round_num} VÒNG RETRY!")
print(f"Tổng sản phẩm lấy thành công: {len(all_products)} / {total_target}")
print(f"ID thất bại cuối cùng: {len(failed_ids)} (nếu >0, kiểm tra file failed cuối cùng để xử lý thủ công)")

# In thử 5 sản phẩm đầu (với fields mới)
for i, p in enumerate(all_products[:5]):
    print(f"{i + 1}. ID: {p['id']} | Tên: {p['name'][:50]}... | Giá: {p['price']:,} ₫")
    print(f"   URL Key: {p['url_key'][:50]}...")
    print(f"   Description: {p['description'][:100]}...")
    print(f"   Images: {len(p['images'])} ảnh (ví dụ: {p['images'][0] if p['images'] else 'N/A'})")

# Lưu JSON đầy đủ (chỉ fields cần)
output_json = "tiki_products_result.json"
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(all_products, f, ensure_ascii=False, indent=2)
print(f"\nĐã lưu JSON (chỉ {', '.join(FIELDS)}) vào: {output_json}")

# Lưu Excel dễ đọc
if all_products:
    df = pd.DataFrame(all_products)
    output_excel = "tiki_products_result.xlsx"
    df.to_excel(output_excel, index=False)
    print(f"Đã lưu Excel vào: {output_excel}")

# Lưu failed cuối cùng
if failed_ids:
    with open("failed_ids_final.txt", "w") as f:
        f.write("\n".join(map(str, failed_ids)))
    print(f"{len(failed_ids)} ID thất bại cuối cùng lưu vào failed_ids_final.txt")
    print("→ Để lấy tiếp, copy failed_ids_final.txt vào CSV mới (cột 'id') và chạy script lại.")

print(
    "\nHoàn thành! Đảm bảo: Không trùng (dùng set), đúng thông tin (kiểm tra ID khớp), retry tự động để lấy đủ nhất có thể.")