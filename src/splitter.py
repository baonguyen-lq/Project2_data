from .config import CONFIG
import json
import os

def run_splitter(input_file, output_prefix):
    items_per_file = CONFIG['splitter']['items_per_file']
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    total = len(data)
    for i in range(0, total, items_per_file):
        chunk = data[i:i + items_per_file]
        part_num = (i // items_per_file) + 1
        output_file = f"{output_prefix}{part_num:03d}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)