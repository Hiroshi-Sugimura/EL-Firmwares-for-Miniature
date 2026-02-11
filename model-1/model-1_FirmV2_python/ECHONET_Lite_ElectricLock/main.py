#!/usr/bin/python3
# for rasp pi pico w

import machine
import sys
import os
import time
import network
import _thread
from EchonetLite import EchonetLite, PDCEDT
from machine import Pin, ADC

# --- センサー設定 ---
DOOR_SENSOR_PIN = ADC(Pin(12))       # ドアセンサー入力
DOOR_CONTROL_PIN = Pin(13, Pin.OUT)  # ドアセンサー電源制御
KEY_PIN = Pin(14, Pin.IN)            # 鍵状態入力
THRESHOLD = 1200                     # ドア開閉の閾値

# --- Wi-Fi設定 ---
WIFI_SSID = 'ssid'
WIFI_PASS = 'pass'

# --- 状態変数 ---
KEY_flag = False
DOOR_flag = False
el = None
recv_running = True

def userSetFunc(ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    """SET要求処理"""
    if deoj != [0x02, 0x6F, 0x01]:
        return False
    print(f"| SET受信: EPC=0x{epc:02X}, EDT={pdcedt}")
    return True

def userGetFunc(ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    """GET要求処理"""
    if deoj != [0x02, 0x6F, 0x01]:
        return False
    print(f"| GET受信: EPC=0x{epc:02X}")
    return True

def userInfFunc(ip, tid, seoj, deoj, esv, opc, epc, pdcedt):
    """INF通知受信"""
    if deoj != [0x02, 0x6F, 0x01]:
        return False
    print(f"| INF受信: EPC=0x{epc:02X}, EDT={pdcedt}")
    return True

# --- INF送信（状態変化通知） ---
def send_inf_notification(epc, edt):
    """EPC: プロパティコード, EDT: データ"""
    global el
    deoj = [0x02, 0x6F, 0x01]
    try:
        el.update(deoj, epc, edt)
        print(f"| INF送信: EPC=0x{epc:02X}, EDT={edt}")
    except Exception as e:
        print(f"| INF送信エラー: {e}")

# --- 受信処理専用スレッド ---
def recv_thread():
    """ECHONET Lite受信処理専用スレッド"""
    global recv_running, el
    while recv_running:
        try:
            el.recvProcess()
        except Exception as e:
            print(f"| 受信エラー: {e}")
        time.sleep(0.01)

# --- Wi-Fi接続 ---
def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    while wlan.isconnected() == False:
        time.sleep(1)
    ip = wlan.ifconfig()[0]
    return ip

# --- メイン ---
try:
    print('| IP:', connect())
    el = EchonetLite([[0x02, 0x6F, 0x01]])

    deoj = [0x02, 0x6F, 0x01]

    # --- プロパティ設定 ---
    el.update(deoj, 0x80, [0x30])  # 動作状態: ON
    el.update(deoj, 0x81, [0xFF])  # 設置場所: 不定
    el.update(deoj, 0x82, [0x00, 0x00, 0x52, 0x01])  # Release R
    el.update(deoj, 0x88, [0x42])  # 異常なし
    el.update(deoj, 0x8A, [0x00, 0x00, 0x77])  # メーカーコード
    el.update(deoj, 0x8E, [0x07, 0xE8, 0x01, 0x01])  # 製造年月日
    el.update(deoj, 0xE0, [0x42])  # 施錠
    el.update(deoj, 0xE3, [0x42])  # ドア閉
    el.update(deoj, 0x9D, [0x80, 0xE0, 0xE3])  # INFマップ
    el.update(deoj, 0x9E, [])  # SET可能プロパティなし
    el.update(deoj, 0x9F, [0x80, 0x81, 0x82, 0x88, 0x8A, 0x8E, 0xE0, 0xE3, 0x9D, 0x9E, 0x9F])

    # --- 受信処理開始 ---
    el.begin(userSetFunc, userGetFunc, userInfFunc)

    # 受信スレッド開始
    _thread.start_new_thread(recv_thread, ())
    print("| 受信スレッド開始")

    # INF通知を送信
    send_inf_notification(0x80, [0x30])

    print("| ECHONET Lite 電気錠 起動完了")
    print("|------------------------")

    # センサー電源を常時ON
    DOOR_CONTROL_PIN.value(1)

    # --- メインループ（センサー監視のみ） ---
    while True:
        # 鍵状態監視
        key_state = KEY_PIN.value()
        if key_state == 1 and KEY_flag != True:
            send_inf_notification(0xE0, [0x41])  # 開錠
            print("| 鍵状態変化: 開錠")
            time.sleep(1)
            KEY_flag = True
        elif key_state == 0 and KEY_flag != False:
            send_inf_notification(0xE0, [0x42])  # 施錠
            print("| 鍵状態変化: 施錠")
            time.sleep(1)
            KEY_flag = False

        # ドア状態監視
        door_value = DOOR_SENSOR_PIN.read()
        if door_value >= THRESHOLD and DOOR_flag != True:
            send_inf_notification(0xE3, [0x41])  # 開
            print(f"| ドア状態変化: 開 (値={door_value})")
            time.sleep(1)
            DOOR_flag = True
        elif door_value < THRESHOLD and DOOR_flag != False:
            send_inf_notification(0xE3, [0x42])  # 閉
            print(f"| ドア状態変化: 閉 (値={door_value})")
            time.sleep(1)
            DOOR_flag = False

        time.sleep(0.1)

except Exception as error:
    print("| except -> exit")
    print(error)
    if os.uname().sysname == 'esp32' or os.uname().sysname == 'rp2':
        sys.print_exception(error)
        print("| plz reboot")
    else:
        os._exit(0)
        
