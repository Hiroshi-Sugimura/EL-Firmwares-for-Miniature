#!/usr/bin/micropython
# for ESP32C3 MicroPython

import machine
import sys
import os
import time
import network
from EchonetLite import EchonetLite, PDCEDT
from machine import Pin, PWM
import neopixel
from Python_Serial_ESP_Wi_Fi_Configurator_Device import ESPWiFiConfigurator

# ========== ハードウェア設定 ==========
# LED ストリップ設定
LEDSTRIP_PIN = 11
LEDSTRIP_NUM = 9

# ファン PWM 設定
FAN_PIN = 6

# NeoPixel LED初期化
pin = machine.Pin(LEDSTRIP_PIN, machine.Pin.OUT)
np = neopixel.NeoPixel(pin, LEDSTRIP_NUM)

# PWM初期化（周波数20kHz、デューティ比16ビット）
pwm = PWM(Pin(FAN_PIN), freq=20000)
pwm.duty_u16(0)

# ========== ファン風量テーブル ==========
# Arduino互換：0-1023スケール → 0-65535（16ビットPWM）にスケーリング
# [OFF, L1, L2, L3, L4, L5, L6, L7, L8]
FANPOWER_TABLE = [int(x * 65535 / 1023) for x in [0, 700, 750, 800, 850, 900, 950, 1000, 1023]]

# ========== グローバル変数（状態管理） ==========
# 電源状態
ac_on = False
lowver_led = False  # LED表示フラグ

# 節電モード
save_energy_mode = False  # False:通常モード、True:節電モード

# LED制御
led_r = 255
led_g = 255
led_b = 255
brightness = 15 + 30 * 5  # 輝度（15 + 30 × レベル）

# ファン制御
fan_power = 0  # 現在のファンPWM値

# 現在の設定値
current_mode = 0x41  # 運転モード（AUTO）
current_fan_level = 0x41  # 風量レベル（AUTO）
current_temp = 0x19  # 設定温度（25℃）

# ========== 運転モード設定テーブル ==========
# 各モードのLED色と初期温度を定義
MODE_CONFIG = {
    0x41: {"name": "AUTO", "rgb": (255, 255, 255), "temp": 0x19},      # 白色、25℃
    0x42: {"name": "COOL", "rgb": (0, 0, 255), "temp": 0x19},          # 青色、25℃
    0x43: {"name": "HOT", "rgb": (255, 35, 0), "temp": 0x19},          # 橙赤色、25℃
    0x44: {"name": "DRY", "rgb": (0, 255, 255), "temp": 0x19},         # 水色、25℃
    0x45: {"name": "WIND", "rgb": (0, 250, 50), "temp": 0xFD},         # 黄緑色
}

# ========== ヘルパー関数 ==========
def set_led_state(color_rgb, brightness_level):
    """
    LED状態を設定（節電モード対応）
    
    Args:
        color_rgb: (R, G, B) タプル、0-255の値
        brightness_level: 輝度値（0-255）
    """
    r, g, b = color_rgb
    for i in range(LEDSTRIP_NUM):
        if save_energy_mode:
            # 節電モード：4個ごとに点灯
            if i % 4 == 0:
                np[i] = (int(r * brightness_level / 255), 
                        int(g * brightness_level / 255), 
                        int(b * brightness_level / 255))
            else:
                np[i] = (0, 0, 0)
        else:
            # 通常モード：全LED点灯
            np[i] = (int(r * brightness_level / 255), 
                    int(g * brightness_level / 255), 
                    int(b * brightness_level / 255))
    np.write()

def set_fan_level(level_code):
    """
    ファン風量を設定
    
    Args:
        level_code: 風量レベルコード (0x31-0x38:L1-L8、0x41:AUTO)
        
    Returns:
        成功=True、失敗=False
    """
    global brightness, fan_power, current_fan_level, lowver_led
    
    level_names = {
        0x31: "L1", 0x32: "L2", 0x33: "L3", 0x34: "L4",
        0x35: "L5", 0x36: "L6", 0x37: "L7", 0x38: "L8", 0x41: "AUTO"
    }
    
    # レベルコードをテーブルインデックスに変換
    if level_code == 0x41:  # AUTO
        level_index = 5
        current_fan_level = 0x41
    elif 0x31 <= level_code <= 0x38:  # Level 1-8
        level_index = level_code - 0x30
        current_fan_level = level_code
    else:
        print(f"| Invalid fan level: 0x{level_code:02X}")
        return False
    
    # 輝度と風量を計算（輝度 = 15 + 30 × レベル）
    brightness = 15 + 30 * level_index
    fan_power = FANPOWER_TABLE[level_index]
    
    # LED表示中の場合、LEDとファンを更新
    if lowver_led:
        set_led_state((led_r, led_g, led_b), brightness)
        pwm.duty_u16(fan_power)
    
    print(f"| Fan: {level_names.get(level_code, '?')}, PWM: {fan_power}")
    return True

def set_energy_mode(mode_code):
    """
    節電動作設定
    
    Args:
        mode_code: 0x41=節電ON、0x42=通常動作
        
    Returns:
        成功=True、失敗=False
    """
    global save_energy_mode, lowver_led
    
    if mode_code == 0x41:  # 節電動作
        save_energy_mode = True
        print("| Energy Saving Mode ON")
    elif mode_code == 0x42:  # 通常動作
        save_energy_mode = False
        print("| Energy Saving Mode OFF")
    else:
        return False
    
    # LED表示中の場合、LED表示を更新
    if lowver_led:
        set_led_state((led_r, led_g, led_b), brightness)
    
    return True

def apply_mode(mode_code):
    """
    運転モードを適用（LED色変更、風量設定、温度設定）
    Arduino互換：AUTO・WINDは0x41、それ以外は0x35に設定
    
    Args:
        mode_code: モードコード (0x41:AUTO、0x42:COOL、0x43:HOT、0x44:DRY、0x45:WIND)
        
    Returns:
        成功=True、失敗=False
    """
    global current_mode, current_fan_level, brightness, fan_power, current_temp
    global led_r, led_g, led_b, lowver_led, el
    
    if mode_code not in MODE_CONFIG:
        return False
    
    # モード設定を取得
    config = MODE_CONFIG[mode_code]
    current_mode = mode_code
    led_r, led_g, led_b = config["rgb"]
    current_temp = config["temp"]
    
    # 全モードで FANPOWER_TABLE[5]を使用（輝度と風量）
    brightness = 15 + 30 * 5
    fan_power = FANPOWER_TABLE[5]
    
    # AUTO・WINDモードは 0x41、それ以外は 0x35（Arduino互換）
    if mode_code == 0x41 or mode_code == 0x45:  # AUTO or WIND
        current_fan_level = 0x41
        fan_display = "AUTO(0x41)"
    else:  # COOL、HOT、DRY
        current_fan_level = 0x35
        fan_display = "L5(0x35)"
    
    # LED表示中の場合、LED色とファンを更新
    if lowver_led:
        set_led_state((led_r, led_g, led_b), brightness)
        pwm.duty_u16(fan_power)
    
    # EchonetLite にモード変更を通知
    el.update([0x01, 0x30, 0x01], 0xB0, [mode_code])
    el.update([0x01, 0x30, 0x01], 0xA0, [current_fan_level])
    el.update([0x01, 0x30, 0x01], 0xB3, [current_temp])
    
    print(f"| Mode: {config['name']}, Fan: {fan_display}, PWM: {fan_power}")
    return True

# ========== EchonetLite コールバック関数 ==========
def userSetFunc( ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    """!
    @brief SET系（SETI、SETC、SETGET）命令を受け取った時に処理するものがあればここに記述
    @param ip (str)
    @param tid (list[int])
    @param seoj (list[int])
    @param deoj (list[int])
    @param esv (int)
    @param opc (int)
    @param epc (int)
    @param pdcedt (PDCEDT)
    @return bool 成功=True, 失敗=False、プロパティがあればTrueにする
    @note SET必要な処理を記述する。プロパティの変化があれば、正しくデバイス情報をUpdateしておくことが重要

    SET系命令の処理（デバイス設定変更時に呼び出される）
    
    Args:
        各種EchonetLiteパラメータ
        
    Returns:
        成功=True、失敗=False
    """
    # エアコン以外のオブジェクトは無視
    if deoj != [0x01, 0x30, 0x01]:
        return False
    
    global ac_on, lowver_led, save_energy_mode, brightness, fan_power, el
    global led_r, led_g, led_b, current_mode, current_fan_level, current_temp
    
    print(f"| SET from: {ip}, EPC: 0x{epc:02X}")
    
    # ESVが SET コマンドでない場合は無視
    if esv not in [EchonetLite.SETI, EchonetLite.SETC]:
        return False
    
    # ========== EPC 0x80：電源制御 ==========
    if epc == 0x80:
        if pdcedt.edt == [0x30]:  # 電源ON
            ac_on = True
            lowver_led = True
            print('| Power ON')
            
            # 現在の風量設定を取得
            try:
                fan_val = el.devices[0].GetPDCEDT(0xA0).getEDT()[0]
            except:
                fan_val = 0x41
            
            # 風量に基づいてファンインデックスを計算
            if fan_val == 0x41:  # AUTO
                fan_index = 5
            else:
                fan_index = fan_val - 0x30
            
            brightness_calc = 15 + 30 * fan_index
            
            # 現在のモードに対応した温度を取得（Arduino互換）
            try:
                mode_val = el.devices[0].GetPDCEDT(0xB0).getEDT()[0]
                if mode_val == 0x42:  # COOL
                    temp_val = el.devices[0].GetPDCEDT(0xB5).getEDT()[0]
                elif mode_val == 0x43:  # HOT
                    temp_val = el.devices[0].GetPDCEDT(0xB6).getEDT()[0]
                elif mode_val == 0x44:  # DRY
                    temp_val = el.devices[0].GetPDCEDT(0xB7).getEDT()[0]
                else:  # AUTO or WIND
                    temp_val = el.devices[0].GetPDCEDT(0xB3).getEDT()[0]
                el.update(deoj, 0xB3, [temp_val])
            except:
                pass
            
            # LED表示
            for i in range(LEDSTRIP_NUM):
                if save_energy_mode:
                    if i % 4 == 0:
                        np[i] = (int(led_r * brightness_calc / 255), 
                                int(led_g * brightness_calc / 255), 
                                int(led_b * brightness_calc / 255))
                    else:
                        np[i] = (0, 0, 0)
                else:
                    np[i] = (int(led_r * brightness_calc / 255), 
                            int(led_g * brightness_calc / 255), 
                            int(led_b * brightness_calc / 255))
            np.write()
            
            # ファンを起動
            fan_power = FANPOWER_TABLE[fan_index]
            pwm.duty_u16(fan_power)
            print(f"| Fan ON: Level {fan_val}, PWM: {fan_power}")
            
            el.update(deoj, epc, pdcedt.edt)
            return True
        
        elif pdcedt.edt == [0x31]:  # 電源OFF
            ac_on = False
            lowver_led = False
            print('| Power OFF')
            
            # LED消灯
            for i in range(LEDSTRIP_NUM):
                np[i] = (0, 0, 0)
            np.write()
            
            # ファン停止
            pwm.duty_u16(FANPOWER_TABLE[0])
            
            el.update(deoj, epc, pdcedt.edt)
            return True
    
    # 以下の操作は電源ONの場合のみ有効
    if not ac_on:
        print('| Power OFF → Operation Ignored')
        return False
    
    # ========== EPC 0x8F：節電動作設定 ==========
    if epc == 0x8F:
        if set_energy_mode(pdcedt.edt[0]):
            el.update(deoj, epc, pdcedt.edt)
            return True
    
    # ========== EPC 0xA0：風量設定 ==========
    if epc == 0xA0:
        if set_fan_level(pdcedt.edt[0]):
            el.update(deoj, epc, pdcedt.edt)
            return True
        return False
    
    # ========== EPC 0xB0：運転モード設定 ==========
    if epc == 0xB0:
        if apply_mode(pdcedt.edt[0]):
            return True
        return False
    
    # ========== EPC 0xB3：温度設定値 ==========
    if epc == 0xB3:
        if len(pdcedt.edt) > 0 and 0x00 <= pdcedt.edt[0] <= 0x32:
            current_temp = pdcedt.edt[0]
            # 対応するモードの温度も更新
            try:
                current_mode_val = el.devices[0].GetPDCEDT(0xB0).getEDT()[0]
                if current_mode_val == 0x42:  # COOL
                    el.update(deoj, 0xB5, pdcedt.edt)
                elif current_mode_val == 0x43:  # HOT
                    el.update(deoj, 0xB6, pdcedt.edt)
                elif current_mode_val == 0x44:  # DRY
                    el.update(deoj, 0xB7, pdcedt.edt)
            except:
                pass
            print(f"| Temperature: {pdcedt.edt[0]}°C")
            el.update(deoj, epc, pdcedt.edt)
            return True
        return False
    
    # ========== EPC 0xB4：除湿相対湿度設定値 ==========
    if epc == 0xB4:
        if len(pdcedt.edt) > 0 and 0x00 <= pdcedt.edt[0] <= 0x64:
            print(f"| Humidity: {pdcedt.edt[0]}%")
            el.update(deoj, epc, pdcedt.edt)
            return True
        return False
    
    # ========== EPC 0xB5：冷房温度設定値 ==========
    if epc == 0xB5:
        if len(pdcedt.edt) > 0 and 0x00 <= pdcedt.edt[0] <= 0x32:
            el.update(deoj, epc, pdcedt.edt)
            return True
        return False
    
    # ========== EPC 0xB6：暖房温度設定値 ==========
    if epc == 0xB6:
        if len(pdcedt.edt) > 0 and 0x00 <= pdcedt.edt[0] <= 0x32:
            el.update(deoj, epc, pdcedt.edt)
            return True
        return False
    
    # ========== EPC 0xB7：除湿温度設定値 ==========
    if epc == 0xB7:
        if len(pdcedt.edt) > 0 and 0x00 <= pdcedt.edt[0] <= 0x32:
            el.update(deoj, epc, pdcedt.edt)
            return True
        return False
    
    print(f"| Unsupported EPC: 0x{epc:02X}")
    return False

def userGetFunc( ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    """!
    @brief GET系（GET、SETGET、INFC）命令を受け取った時に処理するものがあればここに記述
    @param ip (str)
    @param tid (list[int])
    @param seoj (list[int])
    @param deoj (list[int])
    @param esv (int)
    @param opc (int)
    @param epc (int)
    @param pdcedt (PDCEDT)
    @return bool 成功=True, 失敗=False、プロパティがあればTrueにする
    @note GET命令に関しては基本的に内部で処理で返却するので、一般にはここに何も記述しなくてよい。SET命令のときに、正しくデバイス情報をUpdateしておくことが重要
    """
    print("| Get from:", ip)
    print("| TID:", el.getHexString(tid), "SEOJ:", el.getHexString(seoj), "DEOJ:", el.getHexString(deoj), "ESV:", el.getHexString(esv), "OPC:", el.getHexString(opc), "EPC:", el.getHexString(epc), pdcedt.printString())
    # 自分のオブジェクト以外無視
    if deoj != [0x02,0x90,0x01]:
        print("| The object is NOT managed.")
        print("|------------------------")
        return False
    print("| The object is managed.")
    print("|------------------------")
    return True

def userInfFunc( ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    """!
    @brief INF系命令（INF、*_RES、*_SNA）を受け取った時に処理するものがあればここに記述
    @param ip (str)
    @param tid (list[int])
    @param seoj (list[int])
    @param deoj (list[int])
    @param esv (int)
    @param opc (int)
    @param epc (int)
    @param pdcedt (PDCEDT)
    @return bool 成功=True, 失敗=False、プロパティがあればTrueにする
    @note INF命令に関しては一般に、デバイス系では無視、コントローラー系では情報保持をすると思われる。
    """
    # 自分のオブジェクト以外無視
    if deoj != [0x02,0x90,0x01]:
        return False
    print("| INF, RES, SNA from:", ip)
    print("| TID:", el.getHexString(tid), "SEOJ:", el.getHexString(seoj), "DEOJ:", el.getHexString(deoj), "ESV:", el.getHexString(esv), "OPC:", el.getHexString(opc), "EPC:", el.getHexString(epc), pdcedt.printString())
    print("|------------------------")
    return True

# WiFi変数作成
WIFI_SSID = "ssid"
WIFI_PASS = "pass"

# ========== メイン処理 ==========
# main
try:
    # setup
    # print('| IP:', connect() ) # WiFi接続
    
    # Wi-Fi設定・接続管理クラスの初期化（自動的に接続試行とシリアル監視を開始）
    wifi_configurator = ESPWiFiConfigurator(default_ssid=WIFI_SSID, default_pass=WIFI_PASS)
    
    # Wi-Fi接続待ち
    wlan = network.WLAN(network.STA_IF)
    while not wlan.isconnected():
        time.sleep(1)
    print('| IP:', wlan.ifconfig()[0])

    # EchonetLite 初期化（エアコンデバイスコード：0x013001）
    el = EchonetLite([[0x01, 0x30, 0x01]])
    
    deoj = [0x01, 0x30, 0x01]  # デバイスオブジェクトコード
    
    # ========== プロパティ初期化 ==========
    el.update(deoj, 0x80, [0x31])  # 電源: OFF
    el.update(deoj, 0x81, [0xFF])  # 設置場所: 不定
    el.update(deoj, 0x82, [0x00, 0x00, 0x52, 0x01])  # 規格Version
    el.update(deoj, 0x88, [0x42])  # 異常なし
    el.update(deoj, 0x8A, [0x00, 0x00, 0x77])  # メーカーコード（神奈川工科大学）
    el.update(deoj, 0x8E, [0x07, 0xE8, 0x01, 0x01])  # 製造年月日
    el.update(deoj, 0x8F, [0x42])  # 節電動作: 通常
    el.update(deoj, 0xA0, [0x41])  # 風量: AUTO
    el.update(deoj, 0xB0, [0x41])  # モード: AUTO
    el.update(deoj, 0xB3, [0xFD])  # 温度設定値: 不明
    el.update(deoj, 0xB4, [0x32])  # 除湿湿度: 50%
    el.update(deoj, 0xB5, [0x1C])  # 冷房温度: 28℃
    el.update(deoj, 0xB6, [0x14])  # 暖房温度: 20℃
    el.update(deoj, 0xB7, [0x1C])  # 除湿温度: 28℃
    el.update(deoj, 0xBA, [0x32])  # 湿度計測値: 50% 固定
    el.update(deoj, 0xBB, [0x16])  # 温度計測値: 22℃固定
    
    # ========== 対応プロパティリスト ==========
    el.update(deoj, 0x9D, [0x80, 0x8F, 0xA0, 0xB0])  # INF対応プロパティ
    el.update(deoj, 0x9E, [0x80, 0x8F, 0xA0, 0xB0, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7])  # SET対応プロパティ
    el.update(deoj, 0x9F, [0x80, 0x81, 0x82, 0x83, 0x88, 0x8A, 0x8E, 0x8F, 0xA0, 0xB0, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xBA, 0xBB, 0x9D, 0x9E, 0x9F])  # GET対応プロパティ
    
    # EchonetLite 起動（コールバック関数を登録）
    el.begin(userSetFunc, userGetFunc, userInfFunc)
    print("| Aircon Started")
    print("|------------------------")

    # loop
    while True:
        el.recvProcess()
        time.sleep(0.01)
except Exception as error:
    print("| except -> exit")
    print(error)
    if os.uname().sysname == 'esp32' or os.uname().sysname == 'rp2':
        sys.print_exception(error)
        print("| plz reboot")
    else:
        os._exit(0) # sys.exitではwindowsの受信ソケットが解放されないので仕方なく

