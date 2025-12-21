import os
import sys
# Thêm root dự án vào sys.path (fix lỗi import src)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from src.splitter import run_splitter
run_splitter("output/tiki_final_cleaned.json", "output/tiki_part_")