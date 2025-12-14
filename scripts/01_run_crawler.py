from src.crawler import run_crawler, read_ids_from_csv
from src.config import CONFIG
import csv

# Load IDs và chạy crawl (giữ nguyên code từ trước)
all_ids = read_ids_from_csv(CONFIG['crawler']['input_csv'], CONFIG['crawler']['id_column'])
run_crawler(all_ids)