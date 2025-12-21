import os
import sys
# Thêm root dự án vào sys.path (fix lỗi import src)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from src.cleaner import run_cleaner
run_cleaner("output/tiki_products_result.json", "output/tiki_final_cleaned.json")