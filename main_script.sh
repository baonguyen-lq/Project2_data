#!/bin/bash
set -e  # Thoát ngay nếu có lệnh lỗi (có thể tắt bằng comment nếu muốn continue khi lỗi)

# ==================== CẤU HÌNH ====================
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/cron_$(date +%Y%m%d_%H%M%S).log"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"

# Tạo thư mục log nếu chưa có
mkdir -p "$LOG_DIR"

echo "=================================================================" | tee -a "$LOG_FILE"
echo "BẮT ĐẦU CRAWLING - $(date)" | tee -a "$LOG_FILE"
echo "Dự án: $PROJECT_DIR" | tee -a "$LOG_FILE"
echo "=================================================================" | tee -a "$LOG_FILE"

# ==================== CÀI ĐẶT THƯ VIỆN ====================
if [ -f "$REQUIREMENTS" ]; then
    echo "Cài đặt/cập nhật thư viện từ requirements.txt..." | tee -a "$LOG_FILE"
    pip3 install -r "$REQUIREMENTS" >> "$LOG_FILE" 2>&1
else
    echo "Không tìm thấy requirements.txt → bỏ qua cài đặt." | tee -a "$LOG_FILE"
fi

# ==================== HÀM CHẠY SCRIPT ====================
run_script() {
    local script_name="$1"
    local script_path="$SCRIPTS_DIR/$script_name"

    if [ ! -f "$script_path" ]; then
        echo "KHÔNG TÌM THẤY: $script_path → BỎ QUA" | tee -a "$LOG_FILE"
        return 1
    fi

    echo "Đang chạy: $script_name ..." | tee -a "$LOG_FILE"
    python3 "$script_path" >> "$LOG_FILE" 2>&1

    if [ $? -eq 0 ]; then
        echo "$script_name → HOÀN THÀNH THÀNH CÔNG" | tee -a "$LOG_FILE"
    else
        echo "$script_name → CÓ LỖI (xem log chi tiết ở trên)" | tee -a "$LOG_FILE"
        # Không exit toàn script nếu muốn tiếp tục các bước sau (comment dòng dưới nếu cần)
        # exit 1
    fi
    echo "--------------------------------------------------" | tee -a "$LOG_FILE"
}

# ==================== CHẠY THEO THỨ TỰ ====================
run_script "01_run_crawler.py"
run_script "02_clean_data.py"
run_script "03_split_data.py"
run_script "04_validate_failed.py"

# ==================== KẾT THÚC ====================
echo "HOÀN TẤT TOÀN BỘ PIPELINE - $(date)" | tee -a "$LOG_FILE"
echo "Log chi tiết: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=================================================================" | tee -a "$LOG_FILE"