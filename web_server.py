import os
import sys
import json
import time
import socket
import tempfile
import threading
import subprocess
import shutil
import urllib.request
import re
import cv2
import numpy as np
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

def get_local_ip():
    """Lấy địa chỉ IP mạng LAN nội bộ của máy tính"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_screenshot_bytes(app):
    """Chụp màn hình giả lập LDPlayer đang chọn và trả về JPEG bytes"""
    try:
        tab_name, tab_index = app._get_selected_ld_info()
        if tab_index is None:
            return None

        dnconsole_path = os.path.join(app.ld_path, "ldconsole.exe")
        if not os.path.exists(dnconsole_path):
            dnconsole_path = os.path.join(app.ld_path, "dnconsole.exe")

        temp_dir = os.path.join(tempfile.gettempdir(), "ts_origin_web")
        os.makedirs(temp_dir, exist_ok=True)
        temp_screen = os.path.join(temp_dir, f"web_cap_{tab_index}.png")

        if os.path.exists(temp_screen):
            try: os.remove(temp_screen)
            except Exception: pass

        app._exec_cmd([dnconsole_path, "adb", "--index", str(tab_index), "--command", "shell screencap -p /sdcard/web_cap.png"])
        app._exec_cmd([dnconsole_path, "adb", "--index", str(tab_index), "--command", f"pull /sdcard/web_cap.png \"{temp_screen}\""])

        if os.path.exists(temp_screen) and os.path.getsize(temp_screen) > 0:
            d = np.fromfile(temp_screen, dtype=np.uint8)
            img = cv2.imdecode(d, cv2.IMREAD_COLOR)
            try: os.remove(temp_screen)
            except Exception: pass

            if img is not None:
                h, w = img.shape[:2]
                if w > 850:
                    scale = 850.0 / w
                    img = cv2.resize(img, (850, int(h * scale)), interpolation=cv2.INTER_AREA)
                ok, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok:
                    return buf.tobytes()
    except Exception:
        pass
    return None


HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>TS Origin - Mobile Control</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --surface: #111827;
            --surface-card: #162032;
            --border: rgba(255, 255, 255, 0.08);
            --border-active: rgba(56, 189, 248, 0.4);
            --primary: #38bdf8;
            --accent: #ea580c;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }

        body {
            background-color: var(--bg);
            color: var(--text);
            padding-bottom: calc(145px + env(safe-area-inset-bottom, 0px));
            overflow-x: hidden;
            user-select: none;
        }

        /* Top Header */
        .app-header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(17, 24, 39, 0.88);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border-bottom: 1px solid var(--border);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 800;
            font-size: 1.15rem;
            color: var(--primary);
            letter-spacing: -0.5px;
        }

        .status-pill {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 9999px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
            transition: 0.3s;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--success);
            box-shadow: 0 0 8px var(--success);
        }

        .status-dot.running {
            background-color: var(--warning);
            box-shadow: 0 0 8px var(--warning);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.25); }
        }

        /* Tab Content Container */
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .tab-pane {
            display: none;
            flex-direction: column;
            gap: 12px;
            animation: fadeIn 0.25s ease-out;
        }

        .tab-pane.active {
            display: flex;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Cards */
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 15px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .card-title {
            font-size: 0.95rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--primary);
        }

        /* Switch toggle */
        .switch {
            position: relative;
            display: inline-block;
            width: 48px;
            height: 26px;
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #334155;
            transition: 0.3s;
            border-radius: 26px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 20px;
            width: 20px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }

        input:checked + .slider {
            background-color: var(--accent);
        }

        input:checked + .slider:before {
            transform: translateX(22px);
        }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        label {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-muted);
        }

        select {
            background: var(--surface-card);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 10px 12px;
            border-radius: 10px;
            font-size: 0.85rem;
            outline: none;
            cursor: pointer;
            width: 100%;
        }

        select:focus {
            border-color: var(--primary);
        }

        .checkbox-group {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
        }

        .chk-label {
            display: flex;
            align-items: center;
            gap: 6px;
            background: var(--surface-card);
            border: 1px solid var(--border);
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 0.82rem;
            font-weight: 500;
            cursor: pointer;
            user-select: none;
            transition: 0.2s;
        }

        .chk-label:has(input:checked) {
            background: rgba(234, 88, 12, 0.18);
            border-color: var(--accent);
            color: #ffedd5;
        }

        .chk-label input {
            accent-color: var(--accent);
            width: 16px;
            height: 16px;
        }

        /* Screen Preview */
        .preview-box {
            width: 100%;
            border-radius: 12px;
            overflow: hidden;
            background: #000;
            border: 1px solid var(--border);
            position: relative;
            min-height: 220px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 6px 20px rgba(0,0,0,0.5);
        }

        .preview-img {
            width: 100%;
            height: auto;
            display: block;
            object-fit: contain;
        }

        .btn-mini {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255,255,255,0.15);
            color: #fff;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }

        .btn-mini:active {
            transform: scale(0.95);
        }

        /* Team Card */
        .team-list-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }

        .team-box {
            background: #0b0f19;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 8px;
            max-height: 220px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .team-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 10px;
            border-radius: 8px;
            background: var(--surface-card);
            border: 1px solid var(--border);
            font-size: 0.82rem;
            font-weight: 500;
            color: #f1f5f9;
            cursor: pointer;
            transition: 0.2s;
        }

        .team-item:active {
            transform: scale(0.97);
            border-color: var(--accent);
        }

        .btn-del-member {
            background: #ef4444;
            color: white;
            border: none;
            width: 24px;
            height: 24px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Log */
        .log-box {
            background: #050811;
            border: 1px solid #1a2234;
            border-radius: 10px;
            padding: 10px;
            font-family: monospace;
            font-size: 0.78rem;
            min-height: 250px;
            max-height: 380px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .log-entry {
            line-height: 1.4;
            color: #cbd5e1;
            word-break: break-word;
        }

        /* Fixed Action Bar (Floating above tabs) */
        .action-bar {
            position: fixed;
            bottom: calc(58px + env(safe-area-inset-bottom, 0px));
            left: 0;
            right: 0;
            background: rgba(17, 24, 39, 0.95);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border-top: 1px solid var(--border);
            padding: 8px 14px;
            display: flex;
            gap: 8px;
            z-index: 90;
            max-width: 600px;
            margin: 0 auto;
        }

        .btn-action {
            flex: 1;
            padding: 11px 8px;
            border: none;
            border-radius: 10px;
            font-weight: 700;
            font-size: 0.9rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
            transition: 0.2s transform, 0.2s opacity;
        }

        .btn-action:active {
            transform: scale(0.96);
        }

        .btn-run {
            background: linear-gradient(135deg, #059669, #10b981);
            color: white;
            box-shadow: 0 3px 12px rgba(16, 185, 129, 0.35);
        }

        .btn-stop {
            background: linear-gradient(135deg, #dc2626, #ef4444);
            color: white;
            box-shadow: 0 3px 12px rgba(239, 68, 68, 0.35);
        }

        .btn-launch {
            background: linear-gradient(135deg, #0284c7, #38bdf8);
            color: white;
            box-shadow: 0 3px 12px rgba(56, 189, 248, 0.35);
        }

        /* Bottom Tab Navigation Bar */
        .tab-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(9, 13, 22, 0.98);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-top: 1px solid var(--border);
            padding: 4px 8px calc(4px + env(safe-area-inset-bottom, 0px));
            display: flex;
            justify-content: space-around;
            z-index: 100;
            max-width: 600px;
            margin: 0 auto;
        }

        .tab-button {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 3px;
            font-size: 0.72rem;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s color, 0.2s transform;
            border-radius: 8px;
            flex: 1;
        }

        .tab-button .tab-icon {
            font-size: 1.25rem;
            transition: 0.2s transform;
        }

        .tab-button.active {
            color: var(--primary);
        }

        .tab-button.active .tab-icon {
            transform: scale(1.15);
        }

        .tab-button:active {
            transform: scale(0.92);
        }

        .toast {
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            color: #fff;
            padding: 8px 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
            font-size: 0.8rem;
            z-index: 200;
            opacity: 0;
            pointer-events: none;
            transition: 0.3s opacity;
        }
        .toast.show { opacity: 1; }
    </style>
</head>
<body>

    <!-- Header -->
    <header class="app-header">
        <div class="brand">
            <span>⚡ TS Origin</span>
        </div>
        <div class="status-pill" id="statusPill">
            <span class="status-dot" id="statusDot"></span>
            <span id="statusText">Sẵn sàng</span>
        </div>
    </header>

    <div class="container">

        <!-- TAB 1: 👁️ MÀN HÌNH GAME -->
        <div class="tab-pane active" id="tabPane_screen">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">👁️ Màn Hình Trực Tiếp</span>
                    <div style="display:flex; align-items:center; gap:6px;">
                        <button class="btn-mini" onclick="refreshScreenshot()">📸 Chụp Ảnh</button>
                    </div>
                </div>
                <div class="preview-box">
                    <img id="screenImg" class="preview-img" src="/api/screenshot" alt="Màn hình giả lập">
                </div>
                <div style="margin-top:10px; display:flex; justify-content:space-between; align-items:center;">
                    <label style="font-size:0.78rem; font-weight:600; color:var(--text-muted);">
                        <input type="checkbox" id="autoStream" onchange="toggleAutoStream(this.checked)" checked style="accent-color:var(--accent); margin-right:4px;"> Tự làm mới (4s)
                    </label>
                    <span style="font-size:0.75rem; color:#64748b;" id="lblStreamStatus">Đang tự động truyền ảnh</span>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">🖥️ Giả Lập & Máy Chủ</span>
                    <button class="btn-mini" onclick="refreshTabs()">🔄 Quét Lại</button>
                </div>
                <div class="form-grid">
                    <div class="form-group">
                        <label>Tab LDPlayer</label>
                        <select id="selectTab" onchange="onTabChanged(this.value)">
                            <option>Đang nạp tab...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Máy Chủ</label>
                        <select id="selectServer" onchange="onServerChanged(this.value)">
                            <option>Điêu Thuyền</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: ⚙️ HOẠT ĐỘNG (CARD A, B, C, D) -->
        <div class="tab-pane" id="tabPane_activity">
            <!-- Card A: Boss Thế Giới -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">👑 Boss Thế Giới (Card A)</span>
                    <label class="switch">
                        <input type="checkbox" id="switch_A" onchange="onSwitchChanged('A', this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="checkbox-group">
                    <label class="chk-label"><input type="checkbox" id="chk_A1" onchange="onCheckboxChanged('A1', this.checked)"> Boss</label>
                    <label class="chk-label"><input type="checkbox" id="chk_A3" onchange="onCheckboxChanged('A3', this.checked)"> Vé</label>
                </div>
                <div class="form-grid" style="margin-top: 10px;">
                    <div class="form-group">
                        <label>Vị Trí Tướng</label>
                        <select id="combo_A_char" onchange="onComboChanged('A_char', this.value)"></select>
                    </div>
                    <div class="form-group">
                        <label>Số Vé Boss</label>
                        <select id="combo_A_ve" onchange="onComboChanged('A_ve', this.value)">
                            <option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Card B: Phụ Bản Đơn / Đội -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">⚔️ Phụ Bản Đơn / Đội (Card B)</span>
                    <label class="switch">
                        <input type="checkbox" id="switch_B" onchange="onSwitchChanged('B', this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="form-grid">
                    <div class="form-group">
                        <label class="chk-label"><input type="checkbox" id="chk_B_don" onchange="onCheckboxChanged('B_don', this.checked)"> Đơn (Cá Nhân)</label>
                        <select id="combo_B_don_char" onchange="onComboChanged('B_don_char', this.value)" style="margin-top:4px;"></select>
                    </div>
                    <div class="form-group">
                        <label class="chk-label"><input type="checkbox" id="chk_B_doi" onchange="onCheckboxChanged('B_doi', this.checked)"> Đội (Tổ Đội)</label>
                        <select id="combo_B_team_char" onchange="onComboChanged('B_team_char', this.value)" style="margin-top:4px;"></select>
                    </div>
                </div>
                <div class="checkbox-group" style="margin-top: 10px;">
                    <label class="chk-label"><input type="checkbox" id="chk_B1" onchange="onCheckboxChanged('B1', this.checked)"> PB 20</label>
                    <label class="chk-label"><input type="checkbox" id="chk_B2" onchange="onCheckboxChanged('B2', this.checked)"> PB 50</label>
                    <label class="chk-label"><input type="checkbox" id="chk_B3" onchange="onCheckboxChanged('B3', this.checked)"> PB 80</label>
                    <label class="chk-label"><input type="checkbox" id="chk_B4" onchange="onCheckboxChanged('B4', this.checked)"> PB 110</label>
                    <label class="chk-label"><input type="checkbox" id="chk_B5" onchange="onCheckboxChanged('B5', this.checked)"> PB 140</label>
                </div>
            </div>

            <!-- Card C: Dị Giới Đêm -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🌌 Dị Giới Đêm (Card C)</span>
                    <label class="switch">
                        <input type="checkbox" id="switch_C" onchange="onSwitchChanged('C', this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="checkbox-group">
                    <label class="chk-label"><input type="checkbox" id="chk_C1" onchange="onCheckboxChanged('C1', this.checked)"> Phúc Thần</label>
                    <label class="chk-label"><input type="checkbox" id="chk_C2" onchange="onCheckboxChanged('C2', this.checked)"> Ký Lục</label>
                    <label class="chk-label"><input type="checkbox" id="chk_C3" onchange="onCheckboxChanged('C3', this.checked)"> Rút Gọn</label>
                </div>
            </div>

            <!-- Card D: 40 NPC / 2K -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🏆 40 NPC / 2K (Card D)</span>
                    <label class="switch">
                        <input type="checkbox" id="switch_D" onchange="onSwitchChanged('D', this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="checkbox-group">
                    <label class="chk-label"><input type="checkbox" id="chk_D2" onchange="onCheckboxChanged('D2', this.checked)"> Tổ Đội</label>
                    <label class="chk-label"><input type="checkbox" id="chk_D3" onchange="onCheckboxChanged('D3', this.checked)"> 40 NPC</label>
                    <label class="chk-label"><input type="checkbox" id="chk_D4" onchange="onCheckboxChanged('D4', this.checked)"> Nhị Kiều</label>
                </div>
                <div class="form-grid" style="margin-top: 10px;">
                    <div class="form-group">
                        <label>Chế độ 40 NPC</label>
                        <select id="combo_D_chien_dau" onchange="onComboChanged('D_chien_dau', this.value)">
                            <option value="Auto">Auto</option><option value="Click">Click</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Mốc Nhị Kiều</label>
                        <select id="combo_D_tang" onchange="onComboChanged('D_tang', this.value)">
                            <option value="Trệt - 10">Trệt - 10</option><option value="11 - 14">11 - 14</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 3: 👥 TỔ ĐỘI (CARD E) -->
        <div class="tab-pane" id="tabPane_team">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">👥 Quản Lý Tổ Đội (Card E)</span>
                </div>
                <div class="form-grid" style="align-items: center; margin-bottom: 8px;">
                    <label class="chk-label"><input type="checkbox" id="chk_E_quan_su" onchange="onCheckboxChanged('E_quan_su', this.checked)"> Quân Sư</label>
                    <div class="form-group">
                        <label>Chọn Quân Sư</label>
                        <select id="combo_E_quan_su" onchange="onComboChanged('E_quan_su', this.value)"></select>
                    </div>
                </div>
                
                <div class="team-list-container">
                    <div>
                        <label style="display:block; margin-bottom:4px; font-size:0.75rem; color:var(--text-muted);">Tướng Có Sẵn (Chạm để thêm ➔)</label>
                        <div class="team-box" id="list_E_A_box">
                            <div style="color:#64748b; font-size:0.75rem; padding:4px;">Đang nạp...</div>
                        </div>
                    </div>
                    <div>
                        <label style="display:block; margin-bottom:4px; font-size:0.75rem; color:var(--text-muted);">Đội Hình (Chạm ✕ để xóa)</label>
                        <div class="team-box" id="list_E_B_box">
                            <div style="color:#64748b; font-size:0.75rem; padding:4px;">(Trống)</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 4: 📜 NHẬT KÝ HOẠT ĐỘNG -->
        <div class="tab-pane" id="tabPane_logs">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📜 Nhật Ký Hoạt Động</span>
                    <button class="btn-mini" onclick="fetchStatus()">🔄 Làm Mới</button>
                </div>
                <div class="log-box" id="logConsole">
                    <div class="log-entry">Đang nạp nhật ký...</div>
                </div>
            </div>
        </div>

    </div>

    <!-- Thanh Nút Thao Tác Cố Định (Fixed Action Bar) -->
    <div class="action-bar">
        <button class="btn-action btn-launch" onclick="sendAction('launch_game')">🎮 Vào Game</button>
        <button class="btn-action btn-run" id="btnRun" onclick="sendAction('run')">🚀 CHẠY</button>
        <button class="btn-action btn-stop" onclick="sendAction('stop')">🛑 DỪNG</button>
    </div>

    <!-- Thanh Chuyển Tab Đáy Màn Hình (Mobile Bottom Navigation) -->
    <nav class="tab-bar">
        <button class="tab-button active" onclick="switchTab('screen', this)">
            <span class="tab-icon">👁️</span>
            <span>Màn Hình</span>
        </button>
        <button class="tab-button" onclick="switchTab('activity', this)">
            <span class="tab-icon">⚙️</span>
            <span>Hoạt Động</span>
        </button>
        <button class="tab-button" onclick="switchTab('team', this)">
            <span class="tab-icon">👥</span>
            <span>Tổ Đội</span>
        </button>
        <button class="tab-button" onclick="switchTab('logs', this)">
            <span class="tab-icon">📜</span>
            <span>Nhật Ký</span>
        </button>
    </nav>

    <div class="toast" id="toast">Thông báo</div>

    <script>
        let streamTimer = null;

        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
            
            const activePane = document.getElementById('tabPane_' + tabId);
            if (activePane) activePane.classList.add('active');
            if (btn) btn.classList.add('active');
            
            if (tabId === 'screen') refreshScreenshot();
            if (tabId === 'logs') fetchStatus();
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2000);
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                if (!res.ok) return;
                const data = await res.json();
                renderUI(data);
            } catch (e) {}
        }

        function renderUI(data) {
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            const btnRun = document.getElementById('btnRun');

            if (data.is_running) {
                statusDot.className = 'status-dot running';
                statusText.innerText = 'Đang chạy Auto...';
                if (btnRun) {
                    btnRun.innerText = '⏳ ĐANG CHẠY';
                    btnRun.style.opacity = '0.7';
                }
            } else {
                statusDot.className = 'status-dot';
                statusText.innerText = 'Sẵn sàng';
                if (btnRun) {
                    btnRun.innerText = '🚀 CHẠY';
                    btnRun.style.opacity = '1';
                }
            }

            const selectTab = document.getElementById('selectTab');
            selectTab.innerHTML = '';
            (data.tabs || []).forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.innerText = t;
                if (t === data.selected_tab) opt.selected = true;
                selectTab.appendChild(opt);
            });

            const selectServer = document.getElementById('selectServer');
            if (selectServer.children.length <= 1) {
                selectServer.innerHTML = '';
                (data.servers || []).forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s;
                    opt.innerText = s;
                    if (s === data.server) opt.selected = true;
                    selectServer.appendChild(opt);
                });
            } else {
                selectServer.value = data.server;
            }

            const charCombos = ['combo_A_char', 'combo_B_don_char', 'combo_B_team_char'];
            charCombos.forEach(cid => {
                const c = document.getElementById(cid);
                if (c && c.children.length === 0) {
                    (data.char_options || []).forEach(co => {
                        const opt = document.createElement('option');
                        opt.value = co; opt.innerText = co;
                        c.appendChild(opt);
                    });
                }
            });

            // Quân sư options
            const comboQS = document.getElementById('combo_E_quan_su');
            if (comboQS) {
                comboQS.innerHTML = '';
                (data.quan_su_options || ['(Trống)']).forEach(qs => {
                    const opt = document.createElement('option');
                    opt.value = qs; opt.innerText = qs;
                    if (qs === data.selected_quan_su) opt.selected = true;
                    comboQS.appendChild(opt);
                });
            }

            // Danh sách A
            const listABox = document.getElementById('list_E_A_box');
            if (listABox) {
                const availA = (data.list_E_A || []).filter(name => !(data.list_E_B || []).includes(name));
                if (availA.length === 0) {
                    listABox.innerHTML = '<div style="color:#64748b; font-size:0.75rem; padding:6px; text-align:center;">(Đã thêm hết)</div>';
                } else {
                    listABox.innerHTML = availA.map(name => `
                        <div class="team-item" onclick="sendAction('add_to_team', {char_name: '${name}'})">
                            <span>${name}</span>
                            <span style="color:var(--accent); font-weight:700; font-size:0.95rem;">➔</span>
                        </div>
                    `).join('');
                }
            }

            // Danh sách B
            const listBBox = document.getElementById('list_E_B_box');
            if (listBBox) {
                const teamB = data.list_E_B || [];
                if (teamB.length === 0) {
                    listBBox.innerHTML = '<div style="color:#64748b; font-size:0.75rem; padding:6px; text-align:center;">(Trống - bấm ➔ để thêm)</div>';
                } else {
                    listBBox.innerHTML = teamB.map(name => `
                        <div class="team-item">
                            <span>${name}</span>
                            <button class="btn-del-member" onclick="event.stopPropagation(); sendAction('remove_from_team', {char_name: '${name}'})">✕</button>
                        </div>
                    `).join('');
                }
            }

            const now = Date.now();

            for (const [k, v] of Object.entries(data.switches || {})) {
                const id = 'switch_' + k;
                if (userLocks[id] && now < userLocks[id]) continue;
                const el = document.getElementById(id);
                if (el) el.checked = !!v;
            }

            for (const [k, v] of Object.entries(data.checkboxes || {})) {
                const id = 'chk_' + k;
                if (userLocks[id] && now < userLocks[id]) continue;
                const el = document.getElementById(id);
                if (el) el.checked = !!v;
            }

            for (const [k, v] of Object.entries(data.combos || {})) {
                const id = 'combo_' + k;
                if (userLocks[id] && now < userLocks[id]) continue;
                const el = document.getElementById(id);
                if (el && document.activeElement !== el) el.value = v;
            }

            applyDynamicUIRules();

            const logConsole = document.getElementById('logConsole');
            if (data.logs && data.logs.length > 0) {
                logConsole.innerHTML = data.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
                logConsole.scrollTop = logConsole.scrollHeight;
            }
        }

        const userLocks = {};

        function applyDynamicUIRules() {
            const chkD2 = document.getElementById('chk_D2');
            const chkD3 = document.getElementById('chk_D3');
            const chkD4 = document.getElementById('chk_D4');
            const chkBdoi = document.getElementById('chk_B_doi');
            const chkEQS = document.getElementById('chk_E_quan_su');
            const comboEQS = document.getElementById('combo_E_quan_su');
            const comboDChienDau = document.getElementById('combo_D_chien_dau');
            const comboDTang = document.getElementById('combo_D_tang');
            const listABox = document.getElementById('list_E_A_box');
            const listBBox = document.getElementById('list_E_B_box');

            // 1. Quy tắc 40 NPC (D3) và Nhị Kiều (D4) loại trừ nhau tức thì
            if (chkD3 && chkD4) {
                const labelD3 = chkD3.closest('.chk-label');
                const labelD4 = chkD4.closest('.chk-label');

                if (chkD3.checked) {
                    chkD4.checked = false;
                    chkD4.disabled = true;
                    if (labelD4) { labelD4.style.opacity = '0.35'; labelD4.style.pointerEvents = 'none'; }
                    if (labelD3) { labelD3.style.opacity = '1'; labelD3.style.pointerEvents = 'auto'; }
                    if (comboDChienDau) { comboDChienDau.disabled = false; comboDChienDau.style.opacity = '1'; }
                    if (comboDTang) { comboDTang.disabled = true; comboDTang.style.opacity = '0.35'; }
                } else if (chkD4.checked) {
                    chkD3.checked = false;
                    chkD3.disabled = true;
                    if (labelD3) { labelD3.style.opacity = '0.35'; labelD3.style.pointerEvents = 'none'; }
                    if (labelD4) { labelD4.style.opacity = '1'; labelD4.style.pointerEvents = 'auto'; }
                    if (comboDTang) { comboDTang.disabled = false; comboDTang.style.opacity = '1'; }
                    if (comboDChienDau) { comboDChienDau.disabled = true; comboDChienDau.style.opacity = '0.35'; }
                } else {
                    chkD3.disabled = false;
                    chkD4.disabled = false;
                    if (labelD3) { labelD3.style.opacity = '1'; labelD3.style.pointerEvents = 'auto'; }
                    if (labelD4) { labelD4.style.opacity = '1'; labelD4.style.pointerEvents = 'auto'; }
                    if (comboDChienDau) { comboDChienDau.disabled = true; comboDChienDau.style.opacity = '0.35'; }
                    if (comboDTang) { comboDTang.disabled = true; comboDTang.style.opacity = '0.35'; }
                }
            }

            // 2. Quy tắc Tổ Đội (D2) -> Khóa / Mở Quân Sư ở Card E
            if (chkD2 && chkEQS) {
                const isD2 = chkD2.checked;
                chkEQS.disabled = !isD2;
                const qsLabel = chkEQS.closest('.chk-label');
                if (qsLabel) {
                    qsLabel.style.opacity = isD2 ? '1' : '0.35';
                    qsLabel.style.pointerEvents = isD2 ? 'auto' : 'none';
                }
                if (comboEQS) {
                    comboEQS.disabled = !isD2;
                    comboEQS.style.opacity = isD2 ? '1' : '0.35';
                }
            }

            // 3. Quy tắc mở danh sách thành viên Card E (khi tích Đội ở PB hoặc Tổ Đội ở 40NPC)
            const isDoiActive = (chkBdoi && chkBdoi.checked) || (chkD2 && chkD2.checked);
            if (listABox && listBBox) {
                listABox.style.opacity = isDoiActive ? '1' : '0.35';
                listABox.style.pointerEvents = isDoiActive ? 'auto' : 'none';
                listBBox.style.opacity = isDoiActive ? '1' : '0.35';
                listBBox.style.pointerEvents = isDoiActive ? 'auto' : 'none';
            }
        }

        async function sendAction(action, payload = {}, showToastMsg = true) {
            try {
                const res = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action, ...payload})
                });
                const r = await res.json();
                if (showToastMsg && r.msg) showToast(r.msg);
            } catch (e) {
                if (showToastMsg) showToast('Lỗi kết nối');
            }
        }

        function onSwitchChanged(name, value) {
            userLocks['switch_' + name] = Date.now() + 2500;
            sendAction('set_switch', {name, value}, false);
            applyDynamicUIRules();
        }

        function onCheckboxChanged(name, value) {
            userLocks['chk_' + name] = Date.now() + 2500;
            if (name === 'D3' && value) {
                userLocks['chk_D4'] = Date.now() + 2500;
                const chkD4 = document.getElementById('chk_D4');
                if (chkD4) chkD4.checked = false;
            } else if (name === 'D4' && value) {
                userLocks['chk_D3'] = Date.now() + 2500;
                const chkD3 = document.getElementById('chk_D3');
                if (chkD3) chkD3.checked = false;
            }
            sendAction('set_checkbox', {name, value}, false);
            applyDynamicUIRules();
        }

        function onComboChanged(name, value) {
            userLocks['combo_' + name] = Date.now() + 2500;
            sendAction('set_combo', {name, value}, false);
        }

        function onTabChanged(tab) {
            sendAction('set_tab', {tab}, true);
        }

        function onServerChanged(server) {
            sendAction('set_server', {server}, true);
        }

        function refreshTabs() {
            sendAction('refresh_tabs', {}, true);
            showToast('Đang quét lại tab...');
        }

        function refreshScreenshot() {
            const img = document.getElementById('screenImg');
            img.src = '/api/screenshot?t=' + Date.now();
        }

        function toggleAutoStream(enable) {
            if (streamTimer) clearInterval(streamTimer);
            const lbl = document.getElementById('lblStreamStatus');
            if (enable) {
                streamTimer = setInterval(refreshScreenshot, 4000);
                if (lbl) lbl.innerText = 'Đang tự động truyền ảnh (4s)';
            } else {
                if (lbl) lbl.innerText = 'Đã tạm dừng tự động truyền ảnh';
            }
        }

        // Khởi động
        fetchStatus();
        setInterval(fetchStatus, 3000);
        toggleAutoStream(true);
    </script>
</body>
</html>
"""


class ToolWebRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        app = getattr(self.server, "app", None)
        if not app:
            self.send_error(500, "App not ready")
            return

        parsed = self.path.split('?')[0]

        if parsed == "/" or parsed == "/index.html":
            body = HTML_PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            return

        elif parsed == "/api/status":
            tabs = []
            if hasattr(app, 'combo_ld_tabs'):
                tabs = list(app.combo_ld_tabs.cget("values"))
                tabs = [t for t in tabs if t not in ["Đang quét tab...", "Lỗi quét dữ liệu", "Không tìm thấy tab LD nào"]]

            selected_tab, _ = app._get_selected_ld_info() if hasattr(app, '_get_selected_ld_info') else (None, None)

            switches = {
                "A": app.var_switch_A.get() if hasattr(app, 'var_switch_A') else False,
                "B": app.var_switch_B.get() if hasattr(app, 'var_switch_B') else False,
                "C": app.var_switch_C.get() if hasattr(app, 'var_switch_C') else False,
                "D": app.var_switch_D.get() if hasattr(app, 'var_switch_D') else False
            }

            checkboxes = {
                "A1": app.var_A1.get() if hasattr(app, 'var_A1') else False,
                "A3": app.var_A3.get() if hasattr(app, 'var_A3') else False,
                "B_don": app.var_B_don.get() if hasattr(app, 'var_B_don') else False,
                "B_doi": app.var_B_doi.get() if hasattr(app, 'var_B_doi') else False,
                "B1": app.var_B1.get() if hasattr(app, 'var_B1') else False,
                "B2": app.var_B2.get() if hasattr(app, 'var_B2') else False,
                "B3": app.var_B3.get() if hasattr(app, 'var_B3') else False,
                "B4": app.var_B4.get() if hasattr(app, 'var_B4') else False,
                "B5": app.var_B5.get() if hasattr(app, 'var_B5') else False,
                "C1": app.var_C1.get() if hasattr(app, 'var_C1') else False,
                "C2": app.var_C2.get() if hasattr(app, 'var_C2') else False,
                "C3": app.var_C3.get() if hasattr(app, 'var_C3') else False,
                "D2": app.var_D2.get() if hasattr(app, 'var_D2') else False,
                "D3": app.var_D3.get() if hasattr(app, 'var_D3') else False,
                "D4": app.var_D4.get() if hasattr(app, 'var_D4') else False,
                "E_quan_su": app.var_E_quan_su.get() if hasattr(app, 'var_E_quan_su') else False
            }

            combos = {
                "A_char": app.combo_A_char.get() if hasattr(app, 'combo_A_char') else "Xuất Chiến",
                "A_ve": app.combo_A_ve.get() if hasattr(app, 'combo_A_ve') else "1",
                "B_don_char": app.combo_B_don_char.get() if hasattr(app, 'combo_B_don_char') else "Xuất Chiến",
                "B_team_char": app.combo_B_team_char.get() if hasattr(app, 'combo_B_team_char') else "Xuất Chiến",
                "D_team_char": app.combo_D_team_char.get() if hasattr(app, 'combo_D_team_char') else "Xuất Chiến",
                "D_chien_dau": app.combo_D_chien_dau.get() if hasattr(app, 'combo_D_chien_dau') else "Auto",
                "D_tang": app.combo_D_tang.get() if hasattr(app, 'combo_D_tang') else "Trệt - 10",
                "E_quan_su": app.combo_E_quan_su.get() if hasattr(app, 'combo_E_quan_su') else "(Trống)"
            }

            is_running = False
            if hasattr(app, 'btn_run') and app.btn_run.cget("text") == "Đang chạy...":
                is_running = True

            list_E_A = app._get_nhanvat_options() if hasattr(app, '_get_nhanvat_options') else []
            list_E_B = list(getattr(app, 'list_E_B', []))
            quan_su_options = app._get_quan_su_options() if hasattr(app, '_get_quan_su_options') else ["(Trống)"]
            selected_quan_su = app.combo_E_quan_su.get() if hasattr(app, 'combo_E_quan_su') else "(Trống)"

            data = {
                "is_running": is_running,
                "selected_tab": selected_tab or (tabs[0] if tabs else ""),
                "tabs": tabs,
                "server": app.combo_server.get() if hasattr(app, 'combo_server') else "Điêu Thuyền",
                "servers": app._get_server_options() if hasattr(app, '_get_server_options') else ["Điêu Thuyền"],
                "char_options": app._get_character_options() if hasattr(app, '_get_character_options') else ["Xuất Chiến"],
                "list_E_A": list_E_A,
                "list_E_B": list_E_B,
                "quan_su_options": quan_su_options,
                "selected_quan_su": selected_quan_su,
                "switches": switches,
                "checkboxes": checkboxes,
                "combos": combos,
                "logs": getattr(app, 'recent_logs', [])[-40:],
                "local_ip": getattr(app, 'web_ip', get_local_ip()),
                "port": getattr(app, 'web_port', 8080)
            }
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            return

        elif parsed == "/api/screenshot":
            img_bytes = get_screenshot_bytes(app)
            if img_bytes:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(img_bytes)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(img_bytes)
            else:
                svg = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="225" viewBox="0 0 400 225">
                    <rect width="100%" height="100%" fill="#182238"/>
                    <text x="50%" y="50%" fill="#64748b" font-family="sans-serif" font-size="14" text-anchor="middle" dominant-baseline="middle">Chưa thể chụp màn hình (Tab chưa bật hoặc ADB bận)</text>
                </svg>""".encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(svg)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(svg)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        app = getattr(self.server, "app", None)
        if not app:
            self.send_error(500, "App not ready")
            return

        if self.path == "/api/action":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                req = json.loads(body.decode('utf-8'))
            except Exception:
                req = {}

            action = req.get("action")
            msg = "Đã thực thi"

            if action == "run":
                app.after(0, app.xu_ly_nut_chay)
                msg = "▶️ Bắt đầu Chạy Tool!"

            elif action == "stop":
                app.after(0, app.dung_tat_ca_hoat_dong)
                msg = "🛑 Đã Dừng khẩn cấp!"

            elif action == "launch_game":
                app.after(0, app.xu_ly_ts_origin)
                msg = "🎮 Đang mở TS Origin..."

            elif action == "refresh_tabs":
                app.after(0, app.refresh_ld_tabs_async)
                msg = "🔄 Đang quét lại Tab..."

            elif action == "set_tab":
                tab = req.get("tab")
                if tab and hasattr(app, 'combo_ld_tabs'):
                    def _set_t():
                        app.combo_ld_tabs.set(tab)
                        app._on_ld_tab_selected(tab)
                    app.after(0, _set_t)
                    msg = f"Đã chọn tab: {tab}"

            elif action == "set_server":
                server = req.get("server")
                if server and hasattr(app, 'combo_server'):
                    def _set_s():
                        app.combo_server.set(server)
                        app._on_server_changed(server)
                    app.after(0, _set_s)
                    msg = f"Đã chọn máy chủ: {server}"

            elif action == "set_switch":
                s_name = req.get("name")
                s_val = bool(req.get("value"))
                switch_var_name = f"var_switch_{s_name}"
                switch_cb_name = f"_on_switch_{s_name}_toggled"

                if hasattr(app, switch_var_name):
                    def _toggle_sw():
                        getattr(app, switch_var_name).set(s_val)
                        if hasattr(app, switch_cb_name):
                            getattr(app, switch_cb_name)()
                    app.after(0, _toggle_sw)
                    msg = f"Công tắc {s_name}: {'BẬT' if s_val else 'TẮT'}"

            elif action == "set_checkbox":
                cb_name = req.get("name")
                cb_val = bool(req.get("value"))
                var_name = f"var_{cb_name}"

                if hasattr(app, var_name):
                    def _toggle_cb():
                        getattr(app, var_name).set(cb_val)
                        if cb_name in ["D2", "B_doi"] and hasattr(app, '_update_card_E_visibility'):
                            app._update_card_E_visibility()
                            app._on_checkbox_toggled()
                        elif cb_name == "D3" and hasattr(app, '_on_D3_toggled'):
                            app._on_D3_toggled()
                        elif cb_name == "D4" and hasattr(app, '_on_D4_toggled'):
                            app._on_D4_toggled()
                        elif cb_name == "E_quan_su" and hasattr(app, '_on_checkbox_toggled'):
                            app._on_checkbox_toggled()
                        else:
                            app._on_checkbox_toggled()
                    app.after(0, _toggle_cb)
                    msg = f"Ô {cb_name}: {'Tích' if cb_val else 'Bỏ'}"

            elif action == "set_combo":
                c_name = req.get("name")
                c_val = req.get("value")
                combo_widget_name = f"combo_{c_name}"

                if hasattr(app, combo_widget_name):
                    def _set_cmb():
                        getattr(app, combo_widget_name).set(c_val)
                        app._on_checkbox_toggled()
                    app.after(0, _set_cmb)
                    msg = f"Đã đổi {c_name} sang {c_val}"

            elif action == "add_to_team":
                char_name = req.get("char_name")
                if char_name and hasattr(app, '_add_A_to_B_E'):
                    def _add():
                        app.selected_E_list_A_char = char_name
                        app._add_A_to_B_E()
                    app.after(0, _add)
                    msg = f"➕ Đã thêm {char_name} vào Tổ Đội"

            elif action == "remove_from_team":
                char_name = req.get("char_name")
                if char_name and hasattr(app, '_remove_B_item_E'):
                    def _rem():
                        app._remove_B_item_E(char_name)
                    app.after(0, _rem)
                    msg = f"➖ Đã xóa {char_name} khỏi Tổ Đội"

            res_body = json.dumps({"success": True, "msg": msg}, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(res_body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(res_body)
            return

        self.send_error(404, "Not Found")


def start_web_server(app, port=8080):
    """Khởi động Web Server ngầm trên port 8080"""
    local_ip = get_local_ip()
    app.web_ip = local_ip
    app.web_port = port

    for attempt_port in [port, port + 1, port + 2, 5000, 8888]:
        try:
            server = ThreadingHTTPServer(('0.0.0.0', attempt_port), ToolWebRequestHandler)
            server.app = app
            app.web_port = attempt_port
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            local_url = f"http://{local_ip}:{attempt_port}"
            app.log_info(f"🌐 [WEB SERVER] Đang chạy tại: {local_url} (Mở link này trên điện thoại)")
            if hasattr(app, '_update_web_url_ui'):
                app.after(0, app._update_web_url_ui, local_url, False)
            return server
        except OSError:
            continue
        except Exception as e:
            app.log_error(f"Không thể khởi động Web Server: {e}")
            break

    return None


def find_or_download_cloudflared(app):
    """Tìm hoặc tự động tải cloudflared.exe nếu chưa có"""
    app_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)

    local_bin = os.path.join(app_dir, "cloudflared.exe")
    if os.path.exists(local_bin) and os.path.getsize(local_bin) > 1000000:
        return local_bin

    sys_bin = shutil.which("cloudflared")
    if sys_bin:
        return sys_bin

    app.log_info("📥 Đang tự động tải cloudflared.exe từ Cloudflare về máy...")
    download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

    try:
        ps_cmd = f"powershell -Command \"[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('{download_url}', '{local_bin}')\""
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.run(ps_cmd, shell=True, creationflags=creation_flags, timeout=45)
        if os.path.exists(local_bin) and os.path.getsize(local_bin) > 1000000:
            app.log_info("✅ Đã tải xong cloudflared.exe thành công!")
            return local_bin
    except Exception:
        pass

    try:
        curl_bin = shutil.which("curl")
        if curl_bin:
            subprocess.run([curl_bin, "-L", "-o", local_bin, download_url], timeout=45)
            if os.path.exists(local_bin) and os.path.getsize(local_bin) > 1000000:
                app.log_info("✅ Đã tải xong cloudflared.exe thành công!")
                return local_bin
    except Exception:
        pass

    try:
        req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=45) as response, open(local_bin, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        if os.path.exists(local_bin) and os.path.getsize(local_bin) > 1000000:
            app.log_info("✅ Đã tải xong cloudflared.exe thành công!")
            return local_bin
    except Exception as e:
        app.log_error(f"Không thể tải cloudflared: {e}")

    return None


def start_cloudflare_tunnel(app):
    """Khởi động đường truyền Online HTTPS bảo mật truy cập từ xa (4G/Internet) - Kết nối tức thì"""
    def _tunnel_worker():
        port = getattr(app, 'web_port', 8080)
        app.log_info(f"🌐 [4G / ONLINE] Đang khởi tạo đường truyền HTTPS qua cổng {port}...")

        # 1. Thử dùng localhost.run với SSH tích hợp sẵn của Windows (Tạo link tức thì trong 1 giây)
        try:
            ssh_bin = shutil.which("ssh") or "ssh"
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            ssh_cmd = [
                ssh_bin,
                "-T",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                "-R", f"80:127.0.0.1:{port}",
                "nokey@localhost.run"
            ]
            proc = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=creation_flags
            )
            app.cloudflared_proc = proc

            for line in iter(proc.stdout.readline, ''):
                if not line: break
                match = re.search(r'(https://[a-zA-Z0-9-]+\.lhr\.life)', line)
                if match:
                    found_url = match.group(1)
                    app.public_web_url = found_url
                    app.log_info(f"🚀 [4G / ONLINE LINK] Sẵn sàng: {found_url}")
                    if hasattr(app, '_update_web_url_ui'):
                        app.after(0, app._update_web_url_ui, found_url, True)
                    return
        except Exception as e:
            app.log_error(f"Lỗi kết nối SSH Tunnel: {e}")

        # 2. Dự phòng dùng cloudflared.exe
        try:
            bin_path = find_or_download_cloudflared(app)
            if bin_path and os.path.exists(bin_path):
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                cmd = [bin_path, "tunnel", "--url", f"http://127.0.0.1:{port}"]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    creationflags=creation_flags
                )
                app.cloudflared_proc = proc

                for line in iter(proc.stdout.readline, ''):
                    if not line: break
                    match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                    if match:
                        found_url = match.group(1)
                        app.public_web_url = found_url
                        app.log_info(f"🚀 [4G / ONLINE LINK] Sẵn sàng: {found_url}")
                        if hasattr(app, '_update_web_url_ui'):
                            app.after(0, app._update_web_url_ui, found_url, True)
                        return
        except Exception as e:
            app.log_error(f"Lỗi khởi động Cloudflare Tunnel: {e}")

        if hasattr(app, '_on_tunnel_failed'):
            app.after(0, app._on_tunnel_failed)

    threading.Thread(target=_tunnel_worker, daemon=True).start()
