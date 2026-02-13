import network
import time
import machine
import sys
import select
import _thread

class ESPWiFiConfigurator:
    """
    ESP32用 Wi-Fi設定・接続管理クラス
    シリアル通信経由でSSID/PASSの設定変更やリセットを受け付け、
    CSVファイルに保存して管理します。
    """
    def __init__(self, config_file="wifi_config.csv", default_ssid="SSID", default_pass="PASS", auto_start=True):
        """
        初期化処理
        Args:
            config_file (str): 設定保存用CSVファイル名
            default_ssid (str): デフォルトのSSID
            default_pass (str): デフォルトのパスワード
            auto_start (bool): 自動でシリアル監視スレッドを開始するかどうか
        """
        self.config_file = config_file
        self.default_ssid = default_ssid
        self.default_pass = default_pass
        self.running = False
        
        # シリアル入力監視用のポーリングオブジェクト作成
        self.poll = select.poll()
        self.poll.register(sys.stdin, select.POLLIN)
        
        if auto_start:
            self.start_monitoring()
        
        # 初期セットアップ（設定読み込みとWi-Fi接続）
        self.setup()

    def start_monitoring(self):
        """シリアル監視スレッドを開始する"""
        if not self.running:
            self.running = True
            _thread.start_new_thread(self._monitor_loop, ())

    def stop_monitoring(self):
        """シリアル監視スレッドを停止する"""
        self.running = False

    def _monitor_loop(self):
        """シリアル監視ループ（別スレッド用）"""
        while self.running:
            self.update()
            time.sleep(0.1)

    def read_config_lines(self):
        """
        設定ファイル(CSV)から全行を読み込む
        Returns:
            list: ファイルの各行を含むリスト
        """
        try:
            with open(self.config_file, "r") as f:
                lines = f.readlines()
            if len(lines) < 2:
                raise Exception("Invalid config")
            return lines
        except:
            # ファイルがない、または不正な場合はデフォルト値を返す
            # 1行目: デフォルト設定 (T=有効)
            # 2行目: Web設定 (F=無効)
            return [
                f"T,{self.default_ssid},{self.default_pass}\n",
                "F,,\n"
            ]

    def save_config_lines(self, lines):
        """
        設定ファイル(CSV)に全行を書き込む
        Args:
            lines (list): 書き込む行のリスト
        """
        with open(self.config_file, "w") as f:
            for line in lines:
                f.write(line)

    def load_config(self):
        """
        有効なWi-Fi設定(SSID, PASS)を読み込む
        行頭が 'T' となっている行の設定を採用する
        Returns:
            tuple: (ssid, password)
        """
        lines = self.read_config_lines()
        for line in lines:
            parts = line.strip().split(',')
            # フォーマット: T/F, SSID, PASS
            if len(parts) >= 3 and parts[0] == 'T':
                return parts[1], parts[2]
        return self.default_ssid, self.default_pass

    def connect_wifi(self, ssid, password):
        """
        指定されたSSIDとパスワードでWi-Fiに接続する
        Args:
            ssid (str): 接続先SSID
            password (str): パスワード
        """
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        print(f"[ESP] Connecting... SSID={ssid}")
        try:
            wlan.connect(ssid, password)
        except OSError as e:
            print(f"[ESP] Wi-Fi Connection Error: {e}")
            # エラー時もリトライや再設定のために処理を継続
        
        # 接続待機 (最大10秒)
        try_count = 0
        while not wlan.isconnected() and try_count < 20:
            time.sleep(0.5)
            print(".", end="")
            try_count += 1
        print("") # 改行

        if wlan.isconnected():
            # 接続成功時、IPアドレスを表示
            ip = wlan.ifconfig()[0]
            print(f"[ESP] Connected successfully. IP: {ip}")
        else:
            # 接続失敗時のメッセージ表示
            print("[ESP] Failed to connect.")
            print(f"[ESP]Failed to connect. SSID={ssid}")
            print("[ESP] Please send Wi-Fi credentials in the following format:")
            print("SSID,PASS")
            print('[ESP] To reset Wi-Fi, type "RESET"')

    def process_input(self, input_str):
        """
        シリアルからの入力コマンドを処理する
        Args:
            input_str (str): 受信した文字列
        """
        if input_str == "RESET":
            # リセットコマンド受信時
            print("[ESP] Resetting Wi-Fi settings...")
            lines = self.read_config_lines()
            
            # 1行目(デフォルト)を有効(T)にする
            parts0 = lines[0].strip().split(',')
            if len(parts0) >= 3:
                lines[0] = f"T,{parts0[1]},{parts0[2]}\n"
            else:
                lines[0] = f"T,{self.default_ssid},{self.default_pass}\n"
                
            # 2行目(Web設定)を無効(F)にする
            parts1 = lines[1].strip().split(',')
            if len(parts1) >= 3:
                lines[1] = f"F,{parts1[1]},{parts1[2]}\n"
            else:
                lines[1] = "F,,\n"
                
            self.save_config_lines(lines)
            print("[ESP] Wi-Fi settings cleared.")
            print("[ESP] Rebooting...")
            time.sleep(1.5)
            machine.reset() # 再起動
            
        elif "," in input_str:
            # 設定コマンド(SSID,PASS)受信時
            parts = input_str.split(",", 1)
            new_ssid = parts[0]
            new_pass = parts[1]

            if len(new_ssid) > 0 and len(new_pass) > 0:
                print(f"[ESP] Saving Wi-Fi settings... SSID={new_ssid}")
                lines = self.read_config_lines()
                
                # 1行目(デフォルト)を無効(F)にする
                parts0 = lines[0].strip().split(',')
                if len(parts0) >= 3:
                    lines[0] = f"F,{parts0[1]},{parts0[2]}\n"
                else:
                    lines[0] = f"F,{self.default_ssid},{self.default_pass}\n"
                    
                # 2行目(Web設定)を有効(T)にし、新しい設定を保存
                lines[1] = f"T,{new_ssid},{new_pass}\n"
                
                self.save_config_lines(lines)
                print(f"[ESP] Wi-Fi settings saved.: SSID={new_ssid}")
                print("[ESP] Rebooting...")
                time.sleep(1.5)
                machine.reset() # 再起動
            else:
                # フォーマットエラー時のヘルプ表示
                print("[ESP] Please send Wi-Fi credentials in the following format:")
                print("SSID,PASS")
                print('[ESP] To reset Wi-Fi, type "RESET"')
        else:
            # その他の入力時のヘルプ表示
            print("[ESP] Please send Wi-Fi credentials in the following format:")
            print("SSID,PASS")
            print('[ESP] To reset Wi-Fi, type "RESET"')

    def setup(self):
        """
        起動時のセットアップ処理
        設定を読み込んでWi-Fi接続を試みる
        """
        # MicroPythonでは標準入出力でシリアル通信を行うため、Serial.begin等は不要
        
        ssid, password = self.load_config()

        if len(ssid) > 0 and len(password) > 0:
            # 保存された設定で接続
            self.connect_wifi(ssid, password)
        else:
            # デフォルト設定で接続
            self.connect_wifi(self.default_ssid, self.default_pass)

    def update(self):
        """
        メインループから定期的に呼び出す更新処理
        シリアル入力をノンブロッキングでチェックする
        """
        # データがあるかチェック (timeout=0 で即時リターン)
        events = self.poll.poll(0)
        for fd, event in events:
            if event & select.POLLIN:
                try:
                    line = sys.stdin.readline()
                    if line:
                        input_str = line.strip()
                        if input_str:
                            self.process_input(input_str)
                except Exception as e:
                    print(f"[ESP] Serial Read Error: {e}")

if __name__ == "__main__":
    configurator = ESPWiFiConfigurator()
    while True:
        configurator.update()
        time.sleep(0.2)

