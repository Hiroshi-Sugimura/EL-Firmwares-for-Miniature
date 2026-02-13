import tkinter as tk
from tkinter import messagebox, filedialog
import tkinter.ttk as ttk
import csv
import os
import sys
import subprocess
import serial
import serial.tools.list_ports
import time

# ファイルパス定義
WIFI_FILE = 'wifi_config.csv'

def get_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def write_wifi_csv(ssid, password):
    with open(WIFI_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['T',ssid, password])
        writer.writerow(['F','ssid', 'password'])

def run_mpremote_command(cmd, max_retries=3, delay=2.0):
    """mpremoteコマンドをリトライ付きで実行する"""
    last_error = None
    for attempt in range(max_retries):
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            last_error = e
            print(f"Command failed (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    if last_error:
        raise last_error

def check_serial_port_availability(port, timeout=3.0):
    """シリアルポートが使用可能かチェックする（リトライあり）"""
    start_time = time.time()
    while True:
        try:
            s = serial.Serial(port)
            s.close()
            return True
        except serial.SerialException:
            # 時間切れならFalseを返す
            if time.time() - start_time > timeout:
                return False
            # まだ時間があるなら少し待って再試行
            time.sleep(0.5)

def clean_esp32(port):
    """ESP32内の全ファイルを削除してクリーンにする"""
    clean_script = "_clean_esp32_temp.py"
    script_content = """
import os
def rm(p):
    try:
        if os.stat(p)[0] & 0x4000:
            for f in os.listdir(p):
                rm(p + '/' + f)
            os.rmdir(p)
        else:
            os.remove(p)
    except OSError:
        pass

try:
    for f in os.listdir():
        rm(f)
    print("Filesystem cleaned")
except Exception as e:
    print("Clean error:", e)
"""
    try:
        # 一時スクリプト作成
        with open(clean_script, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        print("Cleaning ESP32 filesystem...")
        # スクリプトをESP32上で実行
        run_mpremote_command([sys.executable, '-m', 'mpremote', 'connect', port, 'run', clean_script])
    except Exception as e:

        print(f"Warning: Failed to clean ESP32: {e}")
    finally:
        # 一時スクリプト削除
        if os.path.exists(clean_script):
            os.remove(clean_script)

def flash_files(port, base_path, wifi_source_file):
    try:
        # まずESP32をクリーンにする
        clean_esp32(port)
        print("Waiting for ESP32 to restart...")
        time.sleep(3.0) # クリーン後の再起動待ち

        deferred_main = None

        # 選択されたフォルダ内のファイルを再帰的に書き込み
        for root_dir, dirs, files in os.walk(base_path):
            # 相対パスを計算
            rel_path = os.path.relpath(root_dir, base_path)
            
            # リモートのディレクトリパスを作成
            if rel_path == '.':
                remote_base = ''
            else:
                remote_base = rel_path.replace(os.sep, '/')
            
            # ディレクトリ作成（ルート以外）
            for d in dirs:
                remote_dir = f"{remote_base}/{d}" if remote_base else d
                # __pycache__ などはスキップ
                if d == '__pycache__' or d.startswith('.'):
                    continue
                try:
                    run_mpremote_command([sys.executable, '-m', 'mpremote', 'connect', port, 'fs', 'mkdir', f':{remote_dir}'], max_retries=1)
                    time.sleep(0.2)
                except Exception:

                    pass # 既に存在する場合などは無視

            # ファイル書き込み
            for file in files:
                # 特定のファイルや隠しファイルはスキップ
                # wifi_config.csv は別途書き込むのでスキップ
                if file == 'wifi_config.csv' or file.startswith('.') or file.endswith('.pyc'):
                    continue
                
                local_file = os.path.join(root_dir, file)
                remote_file = f":{remote_base}/{file}" if remote_base else f":{file}"
                
                # main.py は最後に書き込むためにスキップして保存
                if remote_file == ':main.py':
                    deferred_main = (local_file, remote_file)
                    continue

                print(f"Writing {local_file} to {remote_file}")
                run_mpremote_command([sys.executable, '-m', 'mpremote', 'connect', port, 'fs', 'cp', local_file, remote_file])
                time.sleep(0.5)

        # Wi-Fi.csv の書き込み（main.pyの前に書き込む）
        # 指定されたソースファイルを使用する
        print(f"Writing WiFi config from {wifi_source_file}")
        run_mpremote_command([sys.executable, '-m', 'mpremote', 'connect', port, 'fs', 'cp', wifi_source_file, ':wifi_config.csv'])
        time.sleep(0.5)

        # main.py の書き込み（最後に実行）
        if deferred_main:
            local_file, remote_file = deferred_main
            print(f"Writing {local_file} to {remote_file}")
            run_mpremote_command([sys.executable, '-m', 'mpremote', 'connect', port, 'fs', 'cp', local_file, remote_file])
            time.sleep(0.5)



        messagebox.showinfo("完了", f"ESP32 ({port}) への書き込みが完了しました。")

    except subprocess.CalledProcessError as e:
        messagebox.showerror("エラー", f"書き込み中にエラーが発生しました:\n{e}")

def select_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        folder_path_var.set(folder_selected)
        folder_entry.xview_moveto(1)

def select_csv():
    csv_selected = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
    if csv_selected:
        csv_path_var.set(csv_selected)
        csv_entry.xview_moveto(1)

def toggle_wifi_input():
    if use_csv_var.get():
        ssid_entry.config(state='disabled')
        password_entry.config(state='disabled')
        csv_entry.config(state='normal')
        csv_btn.config(state='normal')
    else:
        ssid_entry.config(state='normal')
        password_entry.config(state='normal')
        csv_entry.config(state='disabled')
        csv_btn.config(state='disabled')

def on_submit():
    port = port_var.get()
    folder_path = folder_path_var.get()

    if not port:
        messagebox.showwarning("ポート未選択", "シリアルポートを選択してください。")
        return

    # ポートの使用可能性を事前にチェック
    if not check_serial_port_availability(port, timeout=5.0):
        messagebox.showerror("ポート・エラー", 
                             f"ポート {port} にアクセスできません。\n\n"
                             "【考えられる原因】\n"
                             "1. 前回の書き込み処理が裏で残っている（ゾンビプロセス）\n"
                             "2. VS Codeの拡張機能（Serial Monitor等）が接続している\n"
                             "3. 別のターミナルやアプリが開いている\n\n"
                             "【対処法】\n"
                             "・VS Codeを一度完全に閉じて再起動する\n"
                             "・タスクマネージャーで『python.exe』を終了する\n"
                             "・USBケーブルを抜き差しする")
        return

    if not folder_path:
        messagebox.showwarning("フォルダ未選択", "プログラムフォルダを選択してください。")
        return

    if not os.path.exists(folder_path):
        messagebox.showwarning("エラー", "選択されたフォルダが存在しません。")
        return

    wifi_source = WIFI_FILE # デフォルトは生成される wifi_config.csv

    if use_csv_var.get():
        # CSVファイルを使用する場合
        csv_path = csv_path_var.get()
        if not csv_path:
            messagebox.showwarning("CSV未選択", "読み込むCSVファイルを選択してください。")
            return
        if not os.path.exists(csv_path):
            messagebox.showwarning("エラー", "選択されたCSVファイルが存在しません。")
            return
        wifi_source = csv_path
    else:
        # 手動入力を使用する場合
        ssid = ssid_entry.get().strip()
        password = password_entry.get().strip()
        if not ssid or not password:
            messagebox.showwarning("入力エラー", "SSIDとパスワードを両方入力してください。")
            return
        write_wifi_csv(ssid, password)
        wifi_source = WIFI_FILE

    flash_files(port, folder_path, wifi_source)

def refresh_ports():
    ports = get_serial_ports()
    port_combo['values'] = ports
    if ports:
        port_var.set(ports[0])
    else:
        port_var.set('')

# GUI
root = tk.Tk()
root.title("ESP32-S3 MicroPython 書き込みツール")
root.geometry("600x250")

# カラム設定（中央を伸縮可能に）
root.columnconfigure(1, weight=1)

# ポート選択
tk.Label(root, text="シリアルポート:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
port_var = tk.StringVar()
port_combo = ttk.Combobox(root, textvariable=port_var, values=get_serial_ports(), state="readonly")
port_combo.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

refresh_btn = tk.Button(root, text="ポート更新", command=refresh_ports)
refresh_btn.grid(row=0, column=2, padx=5, pady=5)

# フォルダ選択
tk.Label(root, text="プログラムフォルダ:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
folder_path_var = tk.StringVar()
folder_entry = tk.Entry(root, textvariable=folder_path_var)
folder_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
folder_btn = tk.Button(root, text="選択", command=select_folder)
folder_btn.grid(row=1, column=2, padx=5, pady=5)

# SSID
tk.Label(root, text="SSID:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
ssid_entry = tk.Entry(root)
ssid_entry.grid(row=2, column=1, padx=10, pady=5, columnspan=2, sticky="ew")

# Password
tk.Label(root, text="Password:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
password_entry = tk.Entry(root, show='*')
password_entry.grid(row=3, column=1, padx=10, pady=5, columnspan=2, sticky="ew")

# CSV選択
use_csv_var = tk.BooleanVar()
use_csv_check = tk.Checkbutton(root, text="wifi_config.csvを読み込む", variable=use_csv_var, command=toggle_wifi_input)
use_csv_check.grid(row=4, column=0, padx=10, pady=5, sticky="e")

csv_path_var = tk.StringVar()
csv_entry = tk.Entry(root, textvariable=csv_path_var, state='disabled')
csv_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

csv_btn = tk.Button(root, text="選択", command=select_csv, state='disabled')
csv_btn.grid(row=4, column=2, padx=5, pady=5)

# 書き込みボタン
submit_btn = tk.Button(root, text="書き込む", command=on_submit)
submit_btn.grid(row=5, column=0, columnspan=3, pady=15, padx=10, sticky="ew")

root.mainloop()
