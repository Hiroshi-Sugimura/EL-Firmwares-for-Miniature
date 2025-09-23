//====================================================================
// ECHONET Lite device firmware for Versatile miniature IoT device set (Model 1)
// Software version 2.0
// Download page: https://github.com/Hiroshi-Sugimura/EL-Firmwares-for-Miniature
// Miniature IoT set Project site: https://miniature.sugi-lab.net/
// Copyright (c) 2024 Sugimura Laboratory. All Rights Reserved.
// BSD-3-Clause license
//====================================================================

#include <Arduino.h>
#include <WiFi.h>
#include <Preferences.h>
#include "EL.h"

//--------------LED
#define LEDR 5
#define LEDG 6
#define LEDB 7
#define DOOR_pin 12
#define KEY_pin 14

#define Sore_Aside 1
#define Sore_Bside 2

bool KEYflag = true, DOORflag = false;

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

//--------------EL
#define OBJ_NUM 1

EL echo(elUDP, { { 0x02, 0x6F, 0x01 } } );    //クラス02  電気錠6F  インスタンスコード 01


void printNetData();


//====================================================================
// user用のcallback
// 受信したらこの関数が呼ばれるので、SetやGetに対して動けばよい、基本はSETだけ動けばよい
// 戻り値や引数は決まっている

// bool (*ELCallback) (   tid,  seoj,   deoj,   esv,  opc,  epc, pdc, edt);
bool callback(byte tid[], byte seoj[], byte deoj[], byte esv, byte opc, byte epc, byte pdc, byte edt[]) {
  bool ret = false;                                          // デフォルトで失敗としておく
  if (deoj[0] != 0x02 || deoj[1] != 0x6F) { return false; }  // 照明ではないので無視
  if (deoj[2] != 0x00 && deoj[2] != 0x01) { return false; }  // インスタンスがないので無視

  // -----------------------------------
  // ESVがSETとかGETとかで動作をかえる、基本的にはSETのみ対応すればよい
  switch (esv) {
    // -----------------------------------
    // 動作状態の変更 Set対応
    case EL_SETI:
    case EL_SETC:
      switch (epc) {

        default:
          break;
      }
      break;  // SETI, SETCここまで

    case EL_GET:
      Serial.println("EL_GET");
      Serial.println("EL_GET_EPC:"+String(epc));
      switch (epc) 
      {
         //基本はtrueを返却
        default:
          ret = true;
          break;
      }
      //GETここまで
      break;

    default:  // 基本はtrueを返却
      ret = false;
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
// main loop
void setup() {

  Serial.begin(115200);                         // シリアル開始

  pinMode(DOOR_pin,INPUT_PULLUP);
  pinMode(KEY_pin ,INPUT);
  pinMode(13,OUTPUT);
  digitalWrite(13,HIGH);

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

  echo.begin(callback);  // EL 起動シーケンス

  // 初期値設定(ライブラリでも処理済みだが書き換えるならココ)
  echo.update(0, 0x80, { 0x30 });                                                                          // ON
  echo.update(0, 0x81, { 0xFF });                                                                          // 場所不定
  echo.update(0, 0x82, { 0x00, 0x00, 0x52, 0x01 });                                                        // Release R rev.1
  //echo.update(0, 0x83, { 0x00 });                                                                        // 識別番号未設定
  // ライブラリによる初期設定が[0xfe + メーカーコード + macアドレス12桁 + 0]
  echo.update(0, 0x88, { 0x42 });                                                                               // 異常なし
  echo.update(0, 0x8A, { 0x00, 0x00, 0x77 });                                                                   // 神奈川工科大学(000077)
  echo.update(0, 0x8E, { 0x07, 0xE8, 0x01, 0x01 });                                                             // 製造年月日(2024/01/01)
  echo.update(0, 0xE0, { 0x42 });                                                                               // 開錠
  echo.update(0, 0xE3, { 0x42 });                                                                               // ドア閉じてる
  echo.update(0, 0x9D, { 0x80, 0xE0, 0xE3});                                                                         // INFプロパティマップ
  echo.update(0, 0x9E, { 0x80});                                                                         // Setプロパティマップ
  echo.update(0, 0x9F, { 0x80, 0x81, 0x82, 0x83, 0x88, 0x8A, 0x8E, 0xE0, 0xE3, 0x9D, 0x9E, 0x9F });             // Getプロパティマップ

  echo.printAll();  // 全設定値の確認

  // 電気錠の状態，繋がった宣言として立ち上がったことをコントローラに知らせるINFを飛ばす
  const byte deoj[] = { 0x02, 0x6F, 0x01 };
  const byte edt[] = { 0x01, 0x31 };
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
// main loop
void loop() {

  resetWiFi();

  //Serial.println(analogRead(DOOR_pin));
  if(analogRead(DOOR_pin) >= 1200) //開閉の基準を調整する場合はこの数字を調整　値を下げるとよりシビアになる
  {
    if (DOORflag != true) 
    {
      echo.update(0, 0xE3, { 0x41 });
      const byte deoj[] = { 0x02, 0x6F, 0x01 };
      const byte edt[] = { 0x01, 0x41 };
      echo.sendMultiOPC1(deoj, EL_INF, 0xE3, edt);
      Serial.println("DOOR_Open");
      DOORflag = true;
      delay(100);
    }
  }
  else 
  {
    if (DOORflag != false) 
    {
      echo.update(0, 0xE3, { 0x42 });
      const byte deoj[] = { 0x02, 0x6F, 0x01 };
      const byte edt[] = { 0x01, 0x42 };
      echo.sendMultiOPC1(deoj, EL_INF, 0xE3, edt);
      Serial.println("DOOR_Close");
      DOORflag = false;
      delay(100);
    }
  }

  if(digitalRead(KEY_pin) == HIGH) 
  {
    if (KEYflag != true) 
    {
      echo.update(0, 0xE0, { 0x41 });
      const byte deoj[] = { 0x02, 0x6F, 0x01 };
      const byte edt[] = { 0x01, 0x41 };
      echo.sendMultiOPC1(deoj, EL_INF, 0xE0, edt);
      Serial.println("KEY_Open");
      KEYflag  = true;
      delay(100);
    }
  }
  else {
    if (KEYflag  != false) 
    {
      echo.update(0, 0xE0, { 0x42 });
      const byte deoj[] = { 0x02, 0x6F, 0x01 };
      const byte edt[] = { 0x01, 0x42 };
      echo.sendMultiOPC1(deoj, EL_INF, 0xE0, edt);
      Serial.println("KEY_Close");
      KEYflag  = false;
      delay(100);
    }
  }

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