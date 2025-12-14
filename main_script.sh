#!/bin/bash

# Tiki ETL Runner - Chạy toàn bộ pipeline từ đầu đến cuối
# Usage: ./run_all_etl.sh
# Requirements: Python 3+, pip installed

set -e  # Exit nếu lỗi (bật/tắt tùy ý)

# Cấu hình (sửa nếu cần)
SCRIPTS_DIR="scripts"
LOG_FILE="logs/etl_run.log"
REQUIREMENTS="requirements.txt"

# Kiểm tra và cài thư viện
if [ -f "$REQUIREMENTS" ]; then
    echo "Cài đặt thư viện từ $REQUIREMENTS..."
    pip install -r $REQUIREMENTS >> $LOG_FILE 2>&1
else
    echo "Không tìm thấy $REQUIREMENTS. Bỏ qua cài đặt."
fi

# Chạy từng script theo thứ tự
run_script() {
    script_path="$SCRIPTS_DIR/$1"
    if [ -f "$script_path" ]; then
        echo "Chạy $1..."
        python "$script_path" >> $LOG_FILE 2>&1
        if [ $? -eq 0 ]; then
            echo "$1 hoàn thành thành công."
        else
            echo "Lỗi khi chạy $1. Kiểm tra $LOG_FILE."
        fi
    else
        echo "Không tìm thấy $script_path."
    fi
}

# Thứ tự chạy chính
run_script "01_run_crawler.py"
run_script "02_clean_data.py"
run_script "03_split_data.py"
run_script "04_validate_failed.py"

# Chạy monitor như background (daemon)
monitor_script="$SCRIPTS_DIR/05_monitor.py"
if [ -f "$monitor_script" ]; then
    echo "Chạy monitor (05_monitor.py) ở background..."
    nohup python "$monitor_script" >> $LOG_FILE 2>&1 &
    echo "Monitor started (PID: $!). Kiểm tra $LOG_FILE để theo dõi."
else
    echo "Không tìm thấy $monitor_script."
fi

echo "HOÀN TẤT TOÀN BỘ PIPELINE! Log chi tiết ở $LOG_FILE."
