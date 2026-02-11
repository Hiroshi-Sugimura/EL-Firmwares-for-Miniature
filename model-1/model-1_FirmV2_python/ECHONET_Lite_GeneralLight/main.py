import machine
import sys
import os
import time
import network
from EchonetLite import EchonetLite, PDCEDT
import neopixel

# NeoPixel 初期化（ピン9に14個のLED）
pin = machine.Pin(9, machine.Pin.OUT)
np = neopixel.NeoPixel(pin, 14)

# 定数
MAX_LUMINANCE = 255
BRIGHTNESS_LEVEL = 100  # 0〜100で保持（EchonetのB0は0-100）
LED_R, LED_G, LED_B = 255, 255, 255  # RGB値 (0-255)

def apply_led_state():
    """
    グローバル変数 (LED_R, LED_G, LED_B, BRIGHTNESS_LEVEL) に基づいて
    NeoPixel のLED状態を更新する。
    """
    global LED_R, LED_G, LED_B, BRIGHTNESS_LEVEL

    # BRIGHTNESS_LEVEL (0-100) を NeoPixel 用の 0-255 に変換
    brightness_val = int(BRIGHTNESS_LEVEL * MAX_LUMINANCE / 100)

    # 最終RGB値
    final_r = int(LED_R * brightness_val / MAX_LUMINANCE)
    final_g = int(LED_G * brightness_val / MAX_LUMINANCE)
    final_b = int(LED_B * brightness_val / MAX_LUMINANCE)

    for i in range(np.n):
        np[i] = (final_r, final_g, final_b)
    np.write()
    print(f'| LED Updated: R={final_r}, G={final_g}, B={final_b} (Level {BRIGHTNESS_LEVEL})')

def userSetFunc(ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    global BRIGHTNESS_LEVEL, LED_R, LED_G, LED_B

    if deoj != [0x02, 0x90, 0x01]:
        return False

    print("| Set from:", ip)
    print("| TID:", el.getHexString(tid), "SEOJ:", el.getHexString(seoj), "DEOJ:", el.getHexString(deoj),
          "ESV:", el.getHexString(esv), "OPC:", el.getHexString(opc), "EPC:", el.getHexString(epc), pdcedt.printString())

    edt = pdcedt.edt

    if esv not in (EchonetLite.SETI, EchonetLite.SETC):
        print("| Unsupported ESV")
        return False

    # Power ON/OFF
    if epc == 0x80:
        if edt == [0x30]:  # ON
            print('| Power ON')
            el.update(deoj, epc, edt)  # 状態をEchonet上に記録
            apply_led_state()
            return True
        elif edt == [0x31]:  # OFF
            print('| Power OFF')
            for i in range(np.n):
                np[i] = (0, 0, 0)
            np.write()
            el.update(deoj, epc, edt)
            return True

    # 設置場所
    if epc == 0x81:
        el.update(deoj, epc, edt)
        return True

    # エラー情報
    if epc == 0x88:
        el.update(deoj, epc, edt)
        return True

    # 照度設定 (0-100) 0x32で50
    if epc == 0xB0:
        if len(edt) > 0 and 0 <= edt[0] <= 100:
            BRIGHTNESS_LEVEL = int(edt[0])
            print("| Set Brightness Level B0:", BRIGHTNESS_LEVEL)
            el.update(deoj, epc, [BRIGHTNESS_LEVEL])
            apply_led_state()
            return True
        else:
            return False

    # 点灯モード
    if epc == 0xB6:
        if len(edt) < 1:
            return False
        mode = edt[0]
        # モードに応じて RGB と BRIGHTNESS_LEVEL を設定（BRIGHTNESS_LEVEL は 0-100）
        if mode == 0x41:  # オート
            LED_R, LED_G, LED_B = 255, 255, 255
            BRIGHTNESS_LEVEL = 70
        elif mode == 0x42:  # 通常灯
            LED_R, LED_G, LED_B = 255, 255, 255
            BRIGHTNESS_LEVEL = 100
        elif mode == 0x43:  # 暖色灯
            LED_R, LED_G, LED_B = 255, 150, 0
            BRIGHTNESS_LEVEL = 20
        elif mode == 0x45:  # カラー灯（カラー設定優先、ここでは例として青を選択しない）
            # カラー灯は C0 (RGB) が設定されていることを前提にするため、
            # ここでは BRIGHTNESS_LEVEL のみ設定（既存のRGBはそのまま）
            BRIGHTNESS_LEVEL = 50
        else:
            print("| Unsupported mode:", hex(mode))
            return False

        print(f"| Set Lighting Mode B6: 0x{mode:X}")
        el.update(deoj, epc, [mode])
        el.update(deoj, 0xC0, [LED_R, LED_G, LED_B])
        apply_led_state()
        return True

    # RGB設定
    if epc == 0xC0:
        if len(edt) == 3:
            LED_R, LED_G, LED_B = int(edt[0]), int(edt[1]), int(edt[2])
            print(f"| Set RGB C0: R={LED_R}, G={LED_G}, B={LED_B}")
            el.update(deoj, epc, [LED_R, LED_G, LED_B])
            # カラー灯モードに切り替える
            el.update(deoj, 0xB6, [0x45])
            apply_led_state()
            return True
        else:
            return False

    print("| Unsupported EPC")
    return False

def userGetFunc(ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    print("| Get from:", ip)
    print("| TID:", el.getHexString(tid), "SEOJ:", el.getHexString(seoj), "DEOJ:", el.getHexString(deoj),
          "ESV:", el.getHexString(esv), "OPC:", el.getHexString(opc), "EPC:", el.getHexString(epc), pdcedt.printString())
    if deoj != [0x02, 0x90, 0x01]:
        print("| The object is NOT managed.")
        return False
    print("| The object is managed.")
    return True

def userInfFunc(ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    if deoj != [0x02, 0x90, 0x01]:
        return False
    print("| INF, RES, SNA from:", ip)
    print("| TID:", el.getHexString(tid), "SEOJ:", el.getHexString(seoj), "DEOJ:", el.getHexString(deoj),
          "ESV:", el.getHexString(esv), "OPC:", el.getHexString(opc), "EPC:", el.getHexString(epc), pdcedt.printString())
    return True

# Wi-Fi 設定（テスト用に実際のSSID/PASSを入れてください）
WIFI_SSID = 'SSID'
WIFI_PASS = 'PASS'

def connect():#Wi-Fiの接続確認
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    while not wlan.isconnected():
        time.sleep(1)
    ip = wlan.ifconfig()[0]
    return ip

# 一般照明の状態、繋がった宣言として立ち上がったことをコントローラに知らせるINFを飛ばす
    deoj = [0x05, 0xFF, 0x01]
    edt = [0x01, 0x31]
    el.sendMultiOPC1(deoj, EchonetLite.INF, 0x80, edt)  
    

# main
try:
    print('| IP:', connect())

    el = EchonetLite([[0x02, 0x90, 0x01]])  # General Lighting object

    # 初期状態（消灯）
    for i in range(np.n):
        np[i] = (0, 0, 0)
    np.write()

    # デバイスのプロパティ初期化
    el.update([0x02, 0x90, 0x01], 0x80, [0x31])  # Power OFF
    el.update([0x02, 0x90, 0x01], 0x88, [0x42])  # 異常なし
    el.update([0x02, 0x90, 0x01], 0x8A, [0x00, 0x00, 0x77])  # 製造者コードなど（例）
    el.update([0x02, 0x90, 0x01], 0x8E, [0x07, 0xE8, 0x01, 0x01])  # 製造年月日（例）
    el.update([0x02, 0x90, 0x01], 0xB0, [BRIGHTNESS_LEVEL])  # 照度
    el.update([0x02, 0x90, 0x01], 0xB6, [0x42])  # 通常灯
    el.update([0x02, 0x90, 0x01], 0xC0, [LED_R, LED_G, LED_B])  # 色設定(白)

    # 対応プロパティ
    el.update([0x02, 0x90, 0x01], 0x9D, [0x80, 0xB6])
    el.update([0x02, 0x90, 0x01], 0x9E, [0x80, 0xB0, 0xB6, 0xC0])
    el.update([0x02, 0x90, 0x01], 0x9F, [0x80, 0x81, 0x82, 0x83, 0x88, 0x8A, 0x8E, 0xB0, 0xB6, 0xC0, 0x9D, 0x9E, 0x9F])

    el.begin(userSetFunc, userGetFunc, userInfFunc)
    print("| start")
    print("|------------------------")

    while True:
        el.recvProcess()
        time.sleep(0.5)

except Exception as error:
    print("| except -> exit")
    print(error)
    if os.uname().sysname in ['esp32', 'rp2']:
        sys.print_exception(error)
        print("| plz reboot")
    else:
        os._exit(0)