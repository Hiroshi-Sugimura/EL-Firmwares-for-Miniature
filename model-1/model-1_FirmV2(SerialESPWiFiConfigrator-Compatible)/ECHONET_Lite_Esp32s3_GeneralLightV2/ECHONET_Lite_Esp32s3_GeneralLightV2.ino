//====================================================================
// ECHONET Lite device firmware for Versatile miniature IoT device set (Model 1)
// Software version 1.0
// Download page: https://github.com/Hiroshi-Sugimura/EL-Firmwares-for-Miniature
// Miniature IoT set Project site: https://miniature.sugi-lab.net/
// Copyright (c) 2024 Sugimura Laboratory. All Rights Reserved.
// BSD-3-Clause license
//====================================================================

#include <WiFi.h>
#include "EL.h"
#include <Adafruit_NeoPixel.h>
#include <Preferences.h>

//---------------Wi-Fi
Preferences preferences;
String ssid ;
String password ;
String inputBuffer = ""; // 入力を一時保持するバッファ
int wifi_flag = 0;
// 既定のSSIDとPASS シリアル通信で上書きしたら書き変える
const char* default_ssid = "Wi-FiSSID Change";//頻繫に使用するWi-FiルーターのSSIDに変更
const char* default_pass = "Wi-FiPASS Change";//頻繫に使用するWi-FiルーターのPASSに変更

WiFiUDP elUDP;
IPAddress myip;

//--------------EL config
// EL Object Number
#define OBJ_NUM 1

// Class group code = 住宅・設備関連機器:0x02, クラスコード 一般照明 : 0x90, インスタンスコード 01
EL echo(elUDP, {{0x02, 0x90, 0x01}});

//--------------LED config
#define LED_PIN 9         // NeoPixel output pin
#define LED_NUM 6         // LED seriese number (device number)
#define MAX_LUMINANCE 255 // Luminance limits( max : 255)

Adafruit_NeoPixel strip(LED_NUM, LED_PIN, NEO_GRB + NEO_KHZ800);

uint8_t LED_R = 255, LED_G = 255, LED_B = 255, BRIGHTNESS = MAX_LUMINANCE;

//====================================================================
bool callback(byte tid[], byte seoj[], byte deoj[], byte esv, byte opc, byte epc, byte pdc, byte edt[])
{
  bool ret = false;                       // デフォルトで失敗としておく
  if (deoj[0] != 0x02 || deoj[1] != 0x90) // 一般照明以外を除外
  {
    return false;
  }
  if (deoj[2] != 0x00 && deoj[2] != 0x01) // 該当インスタンス以外を除外
  {
    return false;
  }

  // -----------------------------------
  // ESVがSETとかGETとかで動作をかえる、基本的にはSETのみ対応すればよい
  switch (esv)
  {
  // -----------------------------------
  // 動作状態の変更 Set対応
  case EL_SETI:
  case EL_SETC:
    switch (epc)
    {
    // 電源
    case 0x80:
      if (edt[0] == 0x30)
      {
        Serial.println("電源ON 80 : 30");
        strip.clear();
        strip.setBrightness(BRIGHTNESS);
        for (int i = 0; i < LED_NUM; i++)
          strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
        strip.show();
        echo.update(0, epc, {0x30});
        echo.update(0, 0xB6, {0x42});
        ret = true;
      }
      else if (edt[0] == 0x31)
      {
        Serial.println("電源OFF 80 : 31");
        strip.clear();
        strip.show();
        echo.update(0, epc, {0x31});
        ret = true;
      }
      else
      {
        ret = false;
      }
      break;

    // 照度の設定 edtを[0x00-0x64]で指定することで明るさに反映
    case 0xB0:
      if (0 <= edt[0] && edt[0] <= 100)
      {
        Serial.printf("照度レベル B0 : %d\n", edt[0]);
        strip.clear();
        BRIGHTNESS = int(edt[0]) * (MAX_LUMINANCE / 100);
        strip.setBrightness(BRIGHTNESS);
        for (int i = 0; i < LED_NUM; i++)
          strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
        strip.show();
        echo.update(0, epc, {edt[0]});
        ret = true;
      }
      else
      {
        ret = false;
      }
      break;

    // LED点灯モードの設定 edtを[0x41-0x45]で指定してモードの変更
    case 0xB6:
      switch (edt[0])
      {
      case 0x41:
        Serial.println("点灯モード 自動 B6 : 41");
        LED_R = LED_G = LED_B = 255; // 白
        strip.clear();
        strip.setBrightness(MAX_LUMINANCE * 0.7);
        for (int i = 0; i < LED_NUM; i++)
          strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
        strip.show();
        echo.update(0, epc, {edt[0]});
        echo.update(0, 0xC0, {LED_R, LED_G, LED_B});
        ret = true;
        break;

      case 0x42:
        Serial.println("点灯モード 通常灯 B6 : 42");
        LED_R = LED_G = LED_B = 255; // 白
        strip.clear();
        strip.setBrightness(MAX_LUMINANCE);
        for (int i = 0; i < LED_NUM; i++)
          strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
        strip.show();
        echo.update(0, epc, {edt[0]});
        echo.update(0, 0xC0, {LED_R, LED_G, LED_B});
        ret = true;
        break;

      case 0x43:
        Serial.println("点灯モード 常夜灯 B6 : 43");
        LED_R = 255, LED_G = 48, LED_G = 0;
        strip.clear();
        strip.setBrightness(MAX_LUMINANCE * 0.2);
        for (int i = 0; i < LED_NUM; i++)
          strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
        strip.show();
        echo.update(0, epc, {edt[0]});
        echo.update(0, 0xC0, {LED_R, LED_G, LED_B});
        ret = true;
        break;

      case 0x45:
        Serial.println("点灯モード カラー灯 B6 : 45");
        LED_R = 0, LED_G = 0, LED_B = 255;
        strip.clear();
        strip.setBrightness(MAX_LUMINANCE * 0.5);
        for (int i = 0; i < LED_NUM; i++)
          strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
        strip.show();
        echo.update(0, epc, {edt[0]});
        echo.update(0, 0xC0, {LED_R, LED_G, LED_B});
        ret = true;
        break;

      default:
        ret = false;
        break;
      }
      break;

    // カラー灯モード時RGB設定 edtの6桁でカラーコード指定
    case 0xC0:
      if (0 <= edt[0] && edt[0] <= 255)
      {
        if (0 <= edt[1] && edt[1] <= 255)
        {
          if (0 <= edt[2] && edt[2] <= 255)
          {
            LED_R = edt[0], LED_G = edt[1], LED_B = edt[2];
            Serial.printf("C0 : %d, %d, %d\n", LED_R, LED_G, LED_B);
            strip.clear();
            for (int i = 0; i < LED_NUM; i++)
              strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
            strip.show();
            echo.update(0, epc, {LED_R, LED_G, LED_B});
            echo.update(0, 0xB6, {0x45});
            ret = true;
          }
        }
      }
      break;
    }
    // SETI, SETCここまで
    break;

  case EL_GET:
    break;

  // 基本はtrueを返却
  default:
    ret = true;
    break;
  }

  return ret;
}

void connectWiFi(String ssid, String password) 
{
  WiFi.begin(ssid.c_str(), password.c_str());
  Serial.printf("WiFiに接続中... SSID=%s\n", ssid.c_str());
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    Serial.print(".");
    retry++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n接続成功! IP: %s\n", WiFi.localIP().toString().c_str());
  } 
  else
  {
    Serial.println("\n接続失敗");
    Serial.println("Wi-Fi以下の形式で送信してください\nSSID,PASS\n\nWi-Fiをリセットする場合「RESET」と入力");
  }
}

//====================================================================
// set-up function
void setup()
{

  // シリアル開始
  Serial.begin(115200);

  // LED制御開始
  strip.begin();
  strip.clear();
  strip.setBrightness(0);
  strip.show();

  preferences.begin("wifi-config", false);

  // 保存済みの値を取得
  wifi_flag = preferences.getInt("wifi_flag", 0);
  ssid = preferences.getString("ssid", "");
  password = preferences.getString("password", "");

  if (wifi_flag == 1 && ssid.length() > 0 && password.length() > 0) {
    // 保存済みWiFiに接続
    connectWiFi(ssid, password);
  } else {
    // デフォルトWiFiに接続
    connectWiFi(default_ssid, default_pass);
  }

  printNetData();  // to serial (debug)

  // print your WiFi IP address:
  myip = WiFi.localIP();

  echo.begin(callback); // EL 起動シーケンス

  // 初期値設定
  echo.update(0, 0x80, {0x31});                   // off
  echo.update(0, 0x81, {0xFF});                   // 場所不定
  echo.update(0, 0x82, {0x00, 0x00, 0x52, 0x01}); // Release R rev.1
  // echo.update(0, 0x83, { 0x00 });                                                                        // 識別番号未設定
  //  ライブラリによる初期設定が[0xfe + メーカーコード6桁 + macアドレス12桁 + 0x0e, 0xf0, 0x01, 0x00, 0x00, 0x00, 0x00]
  echo.update(0, 0x88, {0x42});                                                                         // 異常なし
  echo.update(0, 0x8A, {0x00, 0x00, 0x77});                                                             // 神奈川工科大学(000077)
  echo.update(0, 0x8E, {0x07, 0xE8, 0x01, 0x01});                                                       // 製造年月日(2023/01/01)
  echo.update(0, 0xB0, {BRIGHTNESS});                                                                   // 照度
  echo.update(0, 0xB6, {0x42});                                                                         // 通常灯
  echo.update(0, 0xC0, {LED_R, LED_G, LED_B});                                                          // 色設定(白)
  echo.update(0, 0x9D, {0x80, 0xD6});                                                                   // INFプロパティマップ
  echo.update(0, 0x9E, {0x80, 0xB0, 0xB6, 0xC0});                                                       // Setプロパティマップ
  echo.update(0, 0x9F, {0x80, 0x81, 0x82, 0x83, 0x88, 0x8A, 0x8E, 0xB0, 0xB6, 0xC0, 0x9D, 0x9E, 0x9F}); // Getプロパティマップ

  echo.printAll(); // 全設定値の確認

  // 一般照明の状態，繋がった宣言として立ち上がったことをコントローラに知らせるINFを飛ばす
  const byte deoj[] = {0x05, 0xFF, 0x01};
  const byte edt[] = {0x01, 0x31};
  echo.sendMultiOPC1(deoj, EL_INF, 0x80, edt);

  if(WiFi.status() == WL_CONNECTED)
  {
    Serial.printf("\n接続成功! IP: %s\n", WiFi.localIP().toString().c_str());
  }
  else
  {
    Serial.println("\nWi-Fiの接続が出来ていません");
    Serial.println("Wi-Fi以下の形式で送信してください\nSSID,PASS\nWi-Fiをリセットする場合「RESET」と入力");
  }
}

void resetWiFi()
{
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim(); // CR+LF削除

    if (input.equalsIgnoreCase("RESET")) {
      Serial.println("Wi-Fi設定をリセットします...");
      preferences.putInt("wifi_flag", 0);
      preferences.putString("ssid", "");
      preferences.putString("password", "");
      preferences.end();
      ESP.restart();
    }
    else if (input.indexOf(",") > 0) {
      int commaIndex = input.indexOf(",");
      String newSsid = input.substring(0, commaIndex);
      String newPass = input.substring(commaIndex + 1);

      if (newSsid.length() > 0 && newPass.length() > 0) {
        Serial.printf("新しいWi-Fi設定を保存します: SSID=%s\n", newSsid.c_str());
        preferences.putString("ssid", newSsid);
        preferences.putString("password", newPass);
        preferences.putInt("wifi_flag", 1);
        preferences.end();
        ESP.restart();
      } else {
        Serial.println("Wi-Fi以下の形式で送信してください\nSSID,PASS\n\nWi-Fiをリセットする場合「RESET」と入力");
      }
    }
    else {
      Serial.println("以下の形式で送信してください\nSSID,PASS");
    }
  }
}

//====================================================================
// main loop function
void loop()
{
  resetWiFi();
  echo.recvProcess();

  delay(10);
}

//////////////////////////////////////////////////////////////////////
// debug用
//////////////////////////////////////////////////////////////////////
void printNetData() {
  Serial.println("-----------------------------------");

  // IP
  // print your WiFi shield's IP address:
  IPAddress ip = WiFi.localIP();
  Serial.print("IP  Address: ");
  Serial.println(ip);

  IPAddress dgwip = WiFi.gatewayIP();
  Serial.print("DGW Address: ");
  Serial.println(dgwip);

  IPAddress smip = WiFi.subnetMask();
  Serial.print("SM  Address: ");
  Serial.println(smip);

  byte mac[6];
  WiFi.macAddress(mac);
  Serial.print("Arduino MAC: ");
  Serial.print(mac[5], HEX);
  Serial.print(":");
  Serial.print(mac[4], HEX);
  Serial.print(":");
  Serial.print(mac[3], HEX);
  Serial.print(":");
  Serial.print(mac[2], HEX);
  Serial.print(":");
  Serial.print(mac[1], HEX);
  Serial.print(":");
  Serial.println(mac[0], HEX);

  Serial.print("M5 MAC: ");
  Serial.println(WiFi.macAddress());

  Serial.print("M5 MAC(AP): ");
  Serial.println(WiFi.softAPmacAddress());

  Serial.println("-----------------------------------");
}

//////////////////////////////////////////////////////////////////////
// EOF
//////////////////////////////////////////////////////////////////////