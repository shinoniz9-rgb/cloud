import os
import sys
import time
import tempfile
import subprocess
import cv2
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

def get_ld_path():
    """Lấy đường dẫn LDPlayer từ config.json hoặc mặc định"""
    import json
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if "ld_path" in cfg and os.path.exists(cfg["ld_path"]):
                    return cfg["ld_path"]
        except Exception:
            pass
    for path in [r"C:\LDPlayer\LDPlayer9", r"C:\Program Files\LDPlayer\LDPlayer9"]:
        if os.path.exists(path):
            return path
    return r"C:\LDPlayer\LDPlayer9"

def get_adb_device_id(ld_path, tab_index=0):
    """Tìm thiết bị ADB đang kết nối (ưu tiên emulator-5554 hoặc 127.0.0.1:5555/5554)"""
    adb_path = os.path.join(ld_path, "adb.exe")
    if not os.path.exists(adb_path):
        return None
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        res = subprocess.run([adb_path, "devices"], capture_output=True, text=True, creationflags=creation_flags, timeout=10)
        if res and res.stdout:
            lines = res.stdout.strip().splitlines()
            devices = []
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            
            # Khảo sát cổng thích hợp theo tab_index
            port_5554 = f"emulator-{5554 + (tab_index * 2)}"
            port_5555 = f"127.0.0.1:{5555 + (tab_index * 2)}"
            port_5554_ip = f"127.0.0.1:{5554 + (tab_index * 2)}"

            for target in [port_5554, port_5555, port_5554_ip]:
                if target in devices:
                    return target
            if devices:
                return devices[0]
    except Exception:
        pass
    return None

def capture_screenshot(ld_path, tab_index=0):
    """Chụp màn hình giả lập LDPlayer cực kỳ nhanh qua ADB trực tiếp hoặc dnconsole"""
    temp_dir = os.path.join(tempfile.gettempdir(), "ts_origin_debug")
    os.makedirs(temp_dir, exist_ok=True)
    temp_screen = os.path.join(temp_dir, f"screen_debug_{tab_index}.png")
    
    if os.path.exists(temp_screen):
        try: os.remove(temp_screen)
        except Exception: pass

    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    # 1. Thử chụp trực tiếp qua ADB Device ID đã kết nối
    device_id = get_adb_device_id(ld_path, tab_index)
    adb_path = os.path.join(ld_path, "adb.exe")
    
    if device_id and os.path.exists(adb_path):
        try:
            cmd_cap = [adb_path, "-s", device_id, "shell", "screencap", "-p", "/sdcard/debug_cap.png"]
            cmd_pull = [adb_path, "-s", device_id, "pull", "/sdcard/debug_cap.png", temp_screen]
            subprocess.run(cmd_cap, creationflags=creation_flags, timeout=10)
            subprocess.run(cmd_pull, creationflags=creation_flags, timeout=10)
            if os.path.exists(temp_screen) and os.path.getsize(temp_screen) > 0:
                return temp_screen
        except Exception:
            pass

    # 2. Thử chụp qua dnconsole.exe / ldconsole.exe
    dnconsole_path = os.path.join(ld_path, "ldconsole.exe")
    if not os.path.exists(dnconsole_path):
        dnconsole_path = os.path.join(ld_path, "dnconsole.exe")

    if os.path.exists(dnconsole_path):
        try:
            cmd_cap = [dnconsole_path, "adb", "--index", str(tab_index), "--command", "shell screencap -p /sdcard/debug_cap.png"]
            cmd_pull = [dnconsole_path, "pull", "--index", str(tab_index), "--remote", "/sdcard/debug_cap.png", "--local", temp_screen]
            subprocess.run(cmd_cap, creationflags=creation_flags, timeout=10)
            subprocess.run(cmd_pull, creationflags=creation_flags, timeout=10)
            if os.path.exists(temp_screen) and os.path.getsize(temp_screen) > 0:
                return temp_screen
        except Exception:
            pass

    return None

def main():
    tab_index = 0
    custom_image_path = None

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if os.path.exists(arg) and os.path.isfile(arg):
            custom_image_path = arg
        else:
            try:
                tab_index = int(arg)
            except ValueError:
                pass

    ld_path = get_ld_path()
    print("===============================================================")
    if custom_image_path:
        print(f"[TEST] DANG CHAY TEST DO TUONG DONG VOI FILE ANH: {custom_image_path}")
        screen_file = custom_image_path
    else:
        print(f"[TEST] DANG CHAY TEST DO TUONG DONG (THRESHOLD) TRÊN TAB INDEX: {tab_index}")
        print(f"[PATH] Duong dan LDPlayer: {ld_path}")
        print("===============================================================\n")

        print("[+] Dang chup man hinh gia lap...")
        screen_file = capture_screenshot(ld_path, tab_index)
        if not screen_file or not os.path.exists(screen_file):
            print(f"[X] LOI: Khong the chup man hinh tu LDPlayer Tab Index {tab_index}.")
            print("[!] Vui long kiem tra lai ket noi gia lap LDPlayer hoac truyen duong dan file anh!")
            print("    Cu phap: python debug_template_threshold.py [0 hoac file_anh.png]")
            return

    img_screen = cv2.imdecode(np.fromfile(screen_file, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img_screen is None:
        print("[X] LOI: Khong the doc file anh man hinh da chup!")
        return

    debug_img = img_screen.copy()

    templates = [
        "assets/card_top/login/login_auto.png",
        "assets/card_f/f_dung.png",
        "assets/card_f/skill/f_hp.png",
        "assets/card_f/skill/f_sp.png",
        "assets/card_f/skill/f_hs.png"
    ]

    colors = [
        (0, 255, 0),     # Xanh lá - login_auto
        (255, 165, 0),   # Cam - f_dung
        (0, 255, 255),   # Vàng - f_hp
        (255, 0, 255),   # Tím/Hồng - f_sp
        (0, 165, 255)    # Cam nhạt - f_hs
    ]

    print(f"[+] BAT DAU QUET SO KHOP 5 ANH MAU:\n")
    print(f"{'Ten File Anh Mau':<42} | {'Trang Thai':<10} | {'Do Khop Max':<12} | {'Toa Do (x, y)':<15}")
    print("-" * 85)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    for idx, tmpl_rel in enumerate(templates):
        tmpl_full = os.path.join(base_dir, tmpl_rel)
        if not os.path.exists(tmpl_full):
            print(f"{tmpl_rel:<42} | [X] Khong thay| N/A          | N/A")
            continue

        tmpl_mat = cv2.imdecode(np.fromfile(tmpl_full, dtype=np.uint8), cv2.IMREAD_COLOR)
        if tmpl_mat is None:
            print(f"{tmpl_rel:<42} | [X] Loi doc   | N/A          | N/A")
            continue

        th, tw = tmpl_mat.shape[:2]

        res = cv2.matchTemplate(img_screen, tmpl_mat, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        score_pct = max_val * 100.0
        center_x = max_loc[0] + tw // 2
        center_y = max_loc[1] + th // 2

        color = colors[idx % len(colors)]

        top_left = max_loc
        bottom_right = (max_loc[0] + tw, max_loc[1] + th)
        cv2.rectangle(debug_img, top_left, bottom_right, color, 2)

        label_str = f"{os.path.basename(tmpl_rel)} ({score_pct:.1f}%)"
        cv2.putText(debug_img, label_str, (max_loc[0], max(20, max_loc[1] - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

        status_str = "[OK] Thay" if score_pct >= 75.0 else "[!] Thap"
        print(f"{tmpl_rel:<42} | {status_str:<10} | {score_pct:>6.2f}%      | ({center_x}, {center_y})")

    output_debug_file = os.path.join(base_dir, "debug_output.png")
    cv2.imencode(".png", debug_img)[1].tofile(output_debug_file)

    print("-" * 85)
    print(f"\n[OK] DA LUU ANH DEBUG KET QUA TAI: {output_debug_file}")
    print("👉 Hay mo file 'debug_output.png' de xem truc quan vi tri va ti le khop khung anh!")

if __name__ == "__main__":
    main()
