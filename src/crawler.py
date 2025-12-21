import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import time
import random
from datetime import timedelta
from .config import CONFIG

# Khởi tạo biến global ở module level (FIX CHÍNH ĐÂY)
processed_count = 0
times_per_id = []

def read_ids_from_csv(file_path, column_name="id"):
    if not os.path.exists(file_path):
        print(f"Không tìm thấy file: {file_path}")
        return []
    ids = set()
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
    print(f"Đã đọc {len(ids):,} ID hợp lệ (không trùng)")
    return ids

def fetch_product(product_id):
    global processed_count, times_per_id  # Khai báo để modify global
    id_start_time = time.time()  # Bắt đầu đo cho ID này

    url = f"{CONFIG['crawler']['base_url']}{product_id}"  # Sửa BASE_URL thành lowercase nếu config dùng 'base_url'
    for attempt in range(CONFIG['crawler']['retry_count_per_id'] + 1):  # Sử dụng config đúng
        try:
            r = requests.get(url, headers=CONFIG['crawler']['headers'], timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data and data.get('id') == product_id:
                    product = {
                        'id': data.get('id'),
                        'name': data.get('name'),
                        'url_key': data.get('url_key'),
                        'price': data.get('price'),
                        'description': data.get('description') or data.get('short_description', ''),
                        'images': [img.get('large_url') or img.get('base_url', '') for img in data.get('images', [])]
                    }
                    if CONFIG['crawler']['add_delay']:
                        time.sleep(random.uniform(0.1, 0.5))

                    # Ghi nhận thời gian xử lý ID này
                    elapsed = time.time() - id_start_time
                    times_per_id.append(elapsed)

                    return product
                else:
                    elapsed = time.time() - id_start_time
                    times_per_id.append(elapsed)
                    return None
            elif r.status_code == 404:
                elapsed = time.time() - id_start_time
                times_per_id.append(elapsed)
                return None
            elif r.status_code == 429:
                print(f"Rate limit! Chờ 15s cho ID {product_id}...")
                time.sleep(15)
                continue
            else:
                print(f"HTTP {r.status_code} cho ID {product_id}")
        except Exception as e:
            if attempt < CONFIG['crawler']['retry_count_per_id']:
                time.sleep(3)
                continue
            print(f"Lỗi cuối cùng ID {product_id}: {e}")

    # Nếu thất bại hoàn toàn
    elapsed = time.time() - id_start_time
    times_per_id.append(elapsed)
    return None

def run_crawler(all_ids):
    total_target = len(all_ids)
    all_products = []
    failed_ids = all_ids.copy()
    current_failed = []
    start_time = time.time()

    for round_num in range(1, CONFIG['crawler']['retry_rounds'] + 1):
        if not failed_ids:
            print(f"\nĐÃ LẤY HẾT dữ liệu chỉ sau {round_num - 1} vòng!")
            break

        print(f"\n{'=' * 60}")
        print(f"VÒNG {round_num}/{CONFIG['crawler']['retry_rounds'] } - Còn {len(failed_ids):,} ID chưa lấy")
        print(f"{'=' * 60}")

        with ThreadPoolExecutor(max_workers=CONFIG['crawler']['max_workers'] ) as executor:
            future_to_id = {executor.submit(fetch_product, pid): pid for pid in failed_ids}

            for future in as_completed(future_to_id):
                pid = future_to_id[future]
                global processed_count  # Thêm global ở đây vì đang modify ngoài hàm
                processed_count += 1  # Tăng đếm toàn cục

                try:
                    product = future.result()
                    if product:
                        all_products.append(product)
                        print(
                            f"✓ [{processed_count}/{total_target}] ID {pid} → {product['name'][:45]:45} | {product.get('price', 0):,}₫")
                    else:
                        current_failed.append(pid)
                except Exception as e:
                    current_failed.append(pid)
                    print(f"✗ Lỗi nghiêm trọng ID {pid}: {e}")

                # === IN TIẾN ĐỘ REALTIME ===
                if processed_count % 50 == 0 or processed_count == total_target:
                    elapsed_total = time.time() - start_time
                    avg_time = elapsed_total / processed_count if processed_count > 0 else 0
                    eta = (total_target - processed_count) * avg_time if processed_count < total_target else 0
                    print(f"\n--- TIẾN ĐỘ: {processed_count:,}/{total_target:,} "
                          f"({processed_count / total_target * 100:.2f}%) | "
                          f"Avg: {avg_time:.3f}s/ID | "
                          f"ETA: {str(timedelta(seconds=int(eta)))} ---\n")

        failed_ids = current_failed

        if failed_ids:
            with open(f"failed_ids_round_{round_num}.txt", "w") as f:
                f.write("\n".join(map(str, failed_ids)))

    # =================== KẾT QUẢ CUỐI =====================
    total_time = time.time() - start_time
    success_rate = len(all_products) / total_target * 100
    avg_time_per_id = sum(times_per_id) / len(times_per_id) if times_per_id else 0
    total_requests = len(times_per_id)

    print(f"\n{'=' * 70}")
    print(f"HOÀN TẤT CRAWL TIKI!")
    print(f"{'=' * 70}")
    print(f"Thời gian chạy toàn bộ       : {str(timedelta(seconds=int(total_time)))}")
    print(f"Tổng số request đã gửi       : {total_requests:,}")
    print(f"Thời gian trung bình mỗi ID  : {avg_time_per_id:.3f} giây")
    print(f"Tốc độ trung bình            : {1 / avg_time_per_id:.1f} ID/giây")
    print(f"Thành công                   : {len(all_products):,}/{total_target:,} ({success_rate:.2f}%)")
    print(f"Thất bại cuối cùng           : {len(failed_ids):,}")
    print(f"{'=' * 70}")
    # Lưu kết quả
    output_json = "output/tiki_products_result.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)
    print(f"\nĐã lưu JSON: {output_json}")

    if failed_ids:
        with open("output/failed_ids_final.txt", "w") as f:
            f.write("\n".join(map(str, failed_ids)))
        print(f"\n→ {len(failed_ids):,} ID thất bại cuối cùng → failed_ids_final.txt")
        print("   Copy file này làm input mới để crawl tiếp!")
    # Trả về kết quả (để script gọi dùng)
    return all_products, failed_ids