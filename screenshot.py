# -*- coding: utf-8 -*-
import os
import sys
import json
import subprocess
import datetime

# Fix Windows console UTF-8 output encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def capture_emulator_screen(tab_index: str = "0", output_filename: str = None):
    # 1. Đọc đường dẫn ld_path từ config.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    ld_path = "C:\\LDPlayer\\LDPlayer9"

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                ld_path = cfg.get("ld_path", ld_path)
        except Exception as e:
            print(f"[!] Lỗi đọc config.json: {e}")

    # Tìm ldconsole.exe hoặc dnconsole.exe
    dnconsole_path = os.path.join(ld_path, "ldconsole.exe")
    if not os.path.exists(dnconsole_path):
        dnconsole_path = os.path.join(ld_path, "dnconsole.exe")

    if not os.path.exists(dnconsole_path):
        print(f"[X] Không tìm thấy ldconsole.exe hoặc dnconsole.exe tại: {ld_path}")
        return False, None

    # 2. Tạo thư mục screenshots/ lưu ảnh
    out_dir = os.path.join(script_dir, "screenshots")
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_filename:
        output_filename = f"capture_tab_{tab_index}_{timestamp}.png"
    
    local_path = os.path.join(out_dir, output_filename)

    print(f"[*] Đang chụp ảnh màn hình giả lập Tab Index [{tab_index}]...")

    # 3. Lệnh ADB Chụp ảnh màn hình
    remote_remote = "/sdcard/mat_than_cap.png"
    cmd_cap = [dnconsole_path, "adb", "--index", str(tab_index), "--command", f"shell screencap -p {remote_remote}"]
    subprocess.run(cmd_cap, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000 if sys.platform == "win32" else 0)

    # 4. Kéo ảnh từ giả lập về máy tính
    cmd_pull = [dnconsole_path, "pull", "--index", str(tab_index), "--remote", remote_remote, "--local", local_path]
    subprocess.run(cmd_pull, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000 if sys.platform == "win32" else 0)

    # Dự phòng pull qua ADB chuẩn nếu pull ldconsole không thành công
    if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
        cmd_pull_adb = [dnconsole_path, "adb", "--index", str(tab_index), "--command", f"pull {remote_remote} \"{local_path}\""]
        subprocess.run(cmd_pull_adb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000 if sys.platform == "win32" else 0)

    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        size_kb = round(os.path.getsize(local_path) / 1024, 1)
        print(f"[+] ĐÃ CHỤP ẢNH THÀNH CÔNG!")
        print(f"[+] Đường dẫn ảnh: {local_path}")
        print(f"[+] Dung lượng ảnh: {size_kb} KB")
        return True, local_path
    else:
        print("[X] Chụp ảnh màn hình thất bại! Hãy kiểm tra giả lập LDPlayer có đang mở hay không.")
        return False, None

if __name__ == "__main__":
    tab_idx = sys.argv[1] if len(sys.argv) > 1 else "0"
    out_name = sys.argv[2] if len(sys.argv) > 2 else None
    capture_emulator_screen(tab_idx, out_name)
