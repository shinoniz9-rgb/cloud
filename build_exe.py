import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

base_dir = r"c:\Users\Phat\Downloads\ldplayer_tool"
os.chdir(base_dir)

print("============================================================")
print("  ĐANG TIẾN HÀNH ĐÓNG GÓI TS ORIGIN CONTROL SANG FILE .EXE  ")
print("============================================================")
print()

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconsole",
    "--onefile",
    "--name", "TS_Origin_Control",
    "--collect-all", "customtkinter",
    "--add-data", "assets;assets",
    "main.py"
]

print("Executing PyInstaller...")
res = subprocess.run(cmd)

dist_exe = os.path.join(base_dir, "dist", "TS_Origin_Control.exe")
if os.path.exists(dist_exe):
    print("\n📥 Đang sao chép thư mục assets và cloudflared.exe, ngrok.exe vào thư mục dist...")
    dist_assets = os.path.join(base_dir, "dist", "assets")
    src_assets = os.path.join(base_dir, "assets")
    
    if os.path.exists(dist_assets):
        shutil.rmtree(dist_assets)
    shutil.copytree(src_assets, dist_assets)
    
    cf_exe = os.path.join(base_dir, "cloudflared.exe")
    if os.path.exists(cf_exe):
        shutil.copy2(cf_exe, os.path.join(base_dir, "dist", "cloudflared.exe"))
        
    ng_exe = os.path.join(base_dir, "ngrok.exe")
    if os.path.exists(ng_exe):
        shutil.copy2(ng_exe, os.path.join(base_dir, "dist", "ngrok.exe"))

    cfg_file = os.path.join(base_dir, "config.json")
    if os.path.exists(cfg_file):
        shutil.copy2(cfg_file, os.path.join(base_dir, "dist", "config.json"))
        
    print("🧹 Đang dọn dẹp thư mục tạm...")
    build_dir = os.path.join(base_dir, "build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)
        
    spec_file = os.path.join(base_dir, "TS_Origin_Control.spec")
    if os.path.exists(spec_file):
        os.remove(spec_file)

    print("\n============================================================")
    print("  ✅ ĐÓNG GÓI THÀNH CÔNG!")
    print(f"  📁 File chạy của bạn nằm tại: {dist_exe}")
    print("============================================================")
else:
    print("\n❌ Đóng gói thất bại. Vui lòng kiểm tra lại log ở trên.")
