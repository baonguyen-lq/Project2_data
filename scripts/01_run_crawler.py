import os
import sys
# Thêm root dự án vào sys.path (fix lỗi import src)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import src.crawler
from src.config import CONFIG
import csv

# Load IDs và chạy crawl (giữ nguyên code từ trước)
all_ids = src.crawler.read_ids_from_csv(CONFIG['crawler']['input_csv'], CONFIG['crawler']['id_column'])
src.crawler.run_crawler(all_ids)