import os
import sys
import subprocess

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def build():
    print("[BUILD] Bat dau qua trinh dong goi TS_Origin_Control sang .exe...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--uac-admin",
        "--name", "TS_Origin_Control",
        "--add-data", f"{os.path.join(base_dir, 'assets')};assets",
        "--collect-all", "customtkinter",
        "--hidden-import", "pystray",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        os.path.join(base_dir, "main.py")
    ]
    
    config_file = os.path.join(base_dir, "config.json")
    if os.path.exists(config_file):
        cmd.extend(["--add-data", f"{config_file};."])
        
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=base_dir)
    
    if result.returncode == 0:
        dist_dir = os.path.join(base_dir, "dist", "TS_Origin_Control")
        print(f"\n[SUCCESS] Dong goi thanh cong tai: {dist_dir}")
        print(f"[EXE] File: {os.path.join(dist_dir, 'TS_Origin_Control.exe')}")
    else:
        print(f"\n[ERROR] Dong goi that bai: {result.returncode}")

if __name__ == "__main__":
    build()
