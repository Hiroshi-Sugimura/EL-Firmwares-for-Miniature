//====================================================================
// ECHONET Lite device firmware for Versatile miniature IoT device set (Model 1)
// Software version 1.0
// Download page: https://github.com/Hiroshi-Sugimura/EL-Firmwares-for-Miniature
// Miniature IoT set Project site: https://miniature.sugi-lab.net/
// Copyright (c) 2024, Sugimura Laboratory. All Rights Reserved.
// BSD-3-Clause license
//====================================================================

#include <Arduino.h>
#include <WiFi.h>
#include "EL.h"
#include <Adafruit_NeoPixel.h>
#include <Ticker.h>
#include <ESP32Servo.h>

//--------------DEFS
#define LEDSTRIP_PIN 11
#define LEDSTRIP_NUM 9
#define LUMINANCE 255
#define MAX_FANPOWER 255
#define FAN_PIN   6

//--------------VAL
Adafruit_NeoPixel strip(LEDSTRIP_NUM, LEDSTRIP_PIN, NEO_GRB + NEO_KHZ800);
uint8_t LED_R = 255, LED_G = 255, LED_B = 255;
uint8_t FANPOWER = 255;
int pos[6] = {10,95,140,120,110,130}; //0が閉じた状態、1が上、2が下、3が中、4が上中、5が下中

//--------------WIFI
#define WIFI_SSID "wifi ssid"
#define WIFI_PASS "wifi password"

WiFiUDP elUDP;
IPAddress myip;

//--------------EL
#define OBJ_NUM 1

EL echo(elUDP, { { 0x01, 0x30, 0x01 } } );    //クラス01  家庭用エアコン30  インスタンスコード 01

void printNetData();

//====================================================================
// user用のcallback
// 受信したらこの関数が呼ばれるので、SetやGetに対して動けばよい、基本はSETだけ動けばよい
// 戻り値や引数は決まっている

// bool (*ELCallback) (   tid,  seoj,   deoj,   esv,  opc,  epc, pdc, edt);
bool callback(byte tid[], byte seoj[], byte deoj[], byte esv, byte opc, byte epc, byte pdc, byte edt[]) {
  bool ret = false;                                          // デフォルトで失敗としておく
  if (deoj[0] != 0x01 || deoj[1] != 0x30) { return false; }  // エアコンではないので無視
  if (deoj[2] != 0x00 && deoj[2] != 0x01) { return false; }  // インスタンスがないので無視

  // -----------------------------------
  // ESVがSETとかGETとかで動作をかえる、基本的にはSETのみ対応すればよい
  switch (esv) {
    // -----------------------------------
    // 動作状態の変更 Set対応
    case EL_SETI:
    case EL_SETC:
      switch (epc) {
        case 0x80:                                                          // 電源 0x80
          if (edt[0] == 0x30) {                                             // ON 0x30
            Serial.println("ON");                                           // シリアル
            strip.clear();                                                  // LEDテープ
            strip.setBrightness(LUMINANCE);
            for (int i = 0; i < LEDSTRIP_NUM; i++){
              strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
            }
            strip.show();
            //RGBLED(LED_R,LED_G,LED_B);
            //myServo.write(pos[3]);                                          // ルーバー
            //FANPOWER = 255 - MAX_FANPOWER;   
            FANPOWER = 255;                               // 風量
            ledcWrite(FAN_PIN, FANPOWER);                                         // ファン反映
            echo.update(0, epc, { edt[0] });                                // EL更新 ON
            ret = true;                                                     // 処理成功
          }
          else if (edt[0] == 0x31) {                                        // OFF 0x31
            Serial.println("OFF");                                          // シリアル
            strip.clear();                                                  // LEDテープ
            strip.show();                                        // ルーバー
            FANPOWER = 0;                                                 // 風量
            ledcWrite(FAN_PIN, FANPOWER);                                         // ファン反映
            echo.update(0, epc, { edt[0] });                                // EL更新 OFF
            ret = true;                                                     // 処理成功
          }
          else {
            ret = false;                                                    // 処理失敗
          }
          break;

        case 0xA0:                                                          // 風量設定 0xA0
          if (0x31 <= edt[0] && edt[0] <= 0x38) {                           // 風量レベル[0x31--0x38]
            Serial.printf("風量レベル A0: %d\n", edt[0]);                    // シリアル
            int FAN_Tabele[8] = {205, 205, 205 , 215, 225, 235, 245, 255};

            FANPOWER = FAN_Tabele[(edt[0] - 0x31)];               // 風量
            ledcWrite(FAN_PIN, FANPOWER);                                         // ファン反映
            echo.update(0, epc, { edt[0] });                                // EL更新 風量
            ret = true;                                                     // 処理成功
          }

          else if (edt[0] == 0x41){                                         // 風量自動[0x41]
            Serial.printf("レベル A0: 自動 0x41");                           // シリアル
            FANPOWER = int(MAX_FANPOWER / 8) * 7;               // 風量操作
            ledcWrite(FAN_PIN, FANPOWER);                                         // ファン反映
            echo.update(0, epc, { edt[0] });                                // EL更新
            ret = true;                                                     // 処理成功
          }
          else {
            ret = false;                                                    // 処理失敗
          }
          break;

        case 0xA4:                                                          // 風向上下設定 0xA4
          if (0x41 <= edt[0] && edt[0] <= 0x45) {                           // 風向上下[0x41--0x45]
            Serial.printf("風向上下設定 A4: %x\n", edt[0]);                  // シリアル
            //myServo.write(pos[edt[0] - 0x40]);                              // ルーバー
            echo.update(0, epc, { edt[0] });                                // EL更新
            ret = true;                                                     // 処理成功
          }
          else { 
            ret = false;                                                    // 処理失敗
          }
          break;

        case 0xB0:                                                          // 運転モード設定 0xB0
          switch (edt[0]) {
            case 0x41:                                                      // 自動運転[0x41]
              LED_R = 255, LED_G = 255, LED_B = 255;                        // LEDテープ
              strip.clear();
              strip.setBrightness(LUMINANCE);
              for (int i = 0; i < LEDSTRIP_NUM; i++){
                strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
              }
              strip.show();
              //RGBLED(LED_R,LED_G,LED_B);
              FANPOWER = int(MAX_FANPOWER / 8) * 7;              // 風量操作
              ledcWrite(FAN_PIN, FANPOWER);                                       // ファン反映
              //myServo.write(pos[3]);                                        // ルーバー
              echo.update(0, epc, { edt[0] });                              // EL更新
              echo.update(0, 0xA0, { 0x41 });
              echo.update(0, 0xA4, { 0x43 });
              echo.update(0, 0xB3, { 0xFD });
              ret = true;                                                   // 処理成功
              break;

            case 0x42:                                                      // 冷房運転[0x42]
              LED_R = 0, LED_G = 0, LED_B = 255;                            // LEDテープ
              strip.clear();
              strip.setBrightness(LUMINANCE);
              for (int i = 0; i < LEDSTRIP_NUM; i++){
                strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
              }
              strip.show();
              //RGBLED(LED_R,LED_G,LED_B);
              FANPOWER = int(MAX_FANPOWER / 8) * 7;              // 風量操作
              ledcWrite(FAN_PIN, FANPOWER);                                       // ファン反映
              //myServo.write(pos[3]);                                        // ルーバー
              echo.update(0, epc, { edt[0] });                              // EL更新
              echo.update(0, 0xA0, { 0x35 });
              echo.update(0, 0xB3, echo.devices[0].GetPDCEDT(0xB5));
              ret = true;                                                   // 処理成功
              break;

            case 0x43:                                                      // 暖房運転[0x43]
              LED_R = 255, LED_G = 35, LED_B = 0;                          // LEDテープ
              strip.clear();
              strip.setBrightness(LUMINANCE);
              for (int i = 0; i < LEDSTRIP_NUM; i++){
                strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
              }
              strip.show();
              //RGBLED(LED_R,LED_G,LED_B);
              FANPOWER = int(MAX_FANPOWER / 8) * 7;              // 風量操作
              ledcWrite(FAN_PIN, FANPOWER);                                       // ファン反映
              //myServo.write(pos[3]);                                        // ルーバー
              echo.update(0, epc, { edt[0] });                              // EL更新
              echo.update(0, 0xA0, { 0x35 });
              echo.update(0, 0xB3, echo.devices[0].GetPDCEDT(0xB6));
              ret = true;                                                   // 処理成功
              break;

            case 0x44:                                                      // 除湿運転[0x44]
              LED_R = 0, LED_G = 255, LED_B = 255;                          // LEDテープ
              strip.clear();
              strip.setBrightness(LUMINANCE);
              for (int i = 0; i < LEDSTRIP_NUM; i++){
                strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
              }
              strip.show();
              //RGBLED(LED_R,LED_G,LED_B);
              FANPOWER = int(MAX_FANPOWER / 8) * 7;              // 風量操作
              ledcWrite(FAN_PIN, FANPOWER);                                       // ファン反映
              //myServo.write(pos[3]);                                        // ルーバー
              echo.update(0, epc, { edt[0] });                              // EL更新
              echo.update(0, 0xB3, echo.devices[0].GetPDCEDT(0xB7));
              ret = true;                                                   // 処理成功
              break;

            case 0x45:                                                      // 送風運転[0x45]
              LED_R = 0, LED_G = 250, LED_B = 50;                          // LEDテープ
              strip.clear();
              strip.setBrightness(LUMINANCE);
              for (int i = 0; i < LEDSTRIP_NUM; i++){
                strip.setPixelColor(i, strip.Color(LED_R, LED_G, LED_B));
              }
              strip.show();
              //RGBLED(LED_R,LED_G,LED_B);
              FANPOWER = int(MAX_FANPOWER / 8) * 7;              // 風量操作
              ledcWrite(FAN_PIN, FANPOWER);                                       // ファン反映
              //myServo.write(pos[3]);                                        // ルーバー
              echo.update(0, epc, { edt[0] });                              // EL更新
              echo.update(0, 0xB3, { 0xFD });
              ret = true;                                                   // 処理成功
              break;
              
            default:
              ret = false;                                                  // 処理失敗
              break;
          }
          break;

        case 0xB3:                                                          // 温度設定値 0xB3
          if(0x00 <= edt[0] && edt[0] <= 0x32) {                            // 温度設定[0x00--0x32]
            uint8_t* x = const_cast<uint8_t*>(echo.devices[0].GetPDCEDT(0xB0).getEDT());  // x <-- B0-EDT
            if( 0x42  <= *x && *x <=  0x44 ) {                              // 目標温度あり[0x42--0x44]
              Serial.printf("温度設定値 B3: %d\n", edt[0]);                  // シリアル
              Serial.println("対応したモードの設定値も変更 B5-B7");
              echo.update(0, epc, { edt[0] });                              // EL更新
              echo.update(0, *x + 0x73, { edt[0] });
            }
            else {
              echo.update(0, epc, { 0xFD });                                // 目標温度なし
            }
            ret = true;                                                     // 処理成功
          }
          break;

        case 0xB4:                                                          // 除湿モード相対湿度設定値 0xB4
          if (0x00 <= edt[0] && edt[0] <= 0x64) {                           // [0x00--0x64]
            Serial.printf("除湿モード相対湿度設定値 B4: %x\n", edt[0]);       // シリアル
            echo.update(0, epc, { edt[0] });                                // EL更新
            ret = true;                                                     // 処理成功
          }
          else { 
            ret = false;                                                   // 処理失敗
          }
          break;

        case 0xB5:                                                          // 冷房モード温度設定値 0xB5
          if (0x00 <= edt[0] && edt[0] <= 0x32) {
            uint8_t* x = const_cast<uint8_t*>(echo.devices[0].GetPDCEDT(0xB0).getEDT());  // x <-- B0-EDT
            Serial.printf("冷房モード温度設定値 B5: %x\n", edt[0]);          // シリアル
            echo.update(0, epc, { edt[0] });                               // EL更新
            if (*x == 0x42) {                                              // 冷房である
              echo.update(0, 0xB3, { edt[0] });                            // EL更新
            }
            ret = true;                                                    //処理成功
          }
          else { 
            ret = false;                                                   //処理失敗
          }
          break;

        case 0xB6:                                                         // 暖房モード温度設定値 0xB6
          if (0x00 <= edt[0] && edt[0] <= 0x32) {
            uint8_t* x = const_cast<uint8_t*>(echo.devices[0].GetPDCEDT(0xB0).getEDT());  // x <-- B0-EDT
            Serial.printf("暖房モード温度設定値 B6: %d\n", edt[0]);
            if (*x == 0x43) {                                              // 暖房である
              echo.update(0, 0xB3, { edt[0] });                            // EL更新
            }
            echo.update(0, epc, { edt[0] });
            ret = true;
          }
          else { 
            ret = false;
          }
          break;

        case 0xB7:                                                         // 除湿モード温度設定値 0xB7
          if (0x00 <= edt[0] && edt[0] <= 0x32) {
            uint8_t* x = const_cast<uint8_t*>(echo.devices[0].GetPDCEDT(0xB0).getEDT());  // x <-- B0-EDT
            Serial.printf("除湿モード温度設定値 B7: %d\n", edt[0]);
            if (*x == 0x43) {                                              // 除湿である
              echo.update(0, 0xB3, { edt[0] });                            // EL更新
            }
            echo.update(0, epc, { edt[0] });                               // EL更新
            ret = true;
          }
          else { 
            ret = false;
          }
          break;

      }
      break;  // SETI, SETCここまで

    case EL_GET:
      break;

    default:  // 基本はtrueを返却
      ret = true;
      break;
  }

  return ret;
}


//====================================================================
// main loop
void setup() {

  Serial.begin(115200);                         // シリアル開始

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  Serial.println("WiFi Connnected!");

  ledcAttach(FAN_PIN,20000,8);// ファンのPWMを20kHzの8bitでセット
  ledcWrite(FAN_PIN, 0);// ファンのPWM出力を0にする

  //ledcWrite(FAN_PIN, 255);

  strip.begin();                                // LED制御開始
  strip.clear();                                // メモリ上のLED初期化
  strip.setBrightness(0);                       // メモリ上の明るさ初期化
  strip.show();                                 // LEDに反映

  printNetData();  // to serial (debug)

  myip = WiFi.localIP();

  echo.begin(callback);  // EL 起動シーケンス

  // 初期値設定(ライブラリでも処理済みだが書き換えるならココ)
  echo.update(0, 0x80, { 0x31 });                                                                                                 // off
  echo.update(0, 0x81, { 0xFF });                                                                                                 // 場所不定
  echo.update(0, 0x82, { 0x00, 0x00, 0x52, 0x01 });                                                                               // Release R rev.1
  //echo.update(0, 0x83, { 0x00 });                                                                                               // 識別番号未設定
  // ライブラリによる初期設定が[0xfe + メーカーコード + macアドレス12桁 + 0]
  echo.update(0, 0x88, { 0x42 });                                                                                                 // 異常なし
  echo.update(0, 0x8A, { 0x00, 0x00, 0x77 });                                                                                     // 神奈川工科大学(000077)
  echo.update(0, 0x8E, { 0x07, 0xE8, 0x01, 0x01 });                                                                               // 製造年月日(2024/01/01)
  echo.update(0, 0x8F, { 0x42 });                                                                                                 // 節電動作(通常動作)
  echo.update(0, 0xA0, { 0x41 });                                                                                                 // 風量設定(自動)
  echo.update(0, 0xA4, { 0x43 });                                                                                                 // 風向(中)
  echo.update(0, 0xB0, { 0x41 });                                                                                                 // 運転モード(自動)
  echo.update(0, 0xB3, { 0xFD });                                                                                                 // 温度設定値(不明)
  echo.update(0, 0xB4, { 0x32 });                                                                                                 // 相対湿度設定値(50%)
  echo.update(0, 0xB5, { 0x1C });                                                                                                 // 冷房温度(28℃)
  echo.update(0, 0xB6, { 0x14 });                                                                                                 // 暖房温度(20℃)
  echo.update(0, 0xB7, { 0x1C });                                                                                                 // 除湿温度(28℃)
  echo.update(0, 0xBA, { 0xFD });                                                                                                 // 室内相対湿度計測値(計測不能)
  echo.update(0, 0xBB, { 0x7E });                                                                                                 //室内温度計測値(計測不能)
  echo.update(0, 0x9D, { 0x80, 0x8F, 0xA0, 0xB0 });                                                                               // INFプロパティマップ
  echo.update(0, 0x9E, { 0x80, 0x8F, 0xA0, 0xA4, 0xB0, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7 });                                           // Setプロパティマップ
  echo.update(0, 0x9F, { 0x80, 0x81, 0x82, 0x83, 0x88, 0x8A, 0x8E, 0x8F, 0xA0, 0xA4, 0xB0, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xBA, 0xBB, 0x9D, 0x9E, 0x9F }); // Getプロパティマップ(自動変換)

  echo.printAll();  // 全設定値の確認


  // 一般照明の状態，繋がった宣言として立ち上がったことをコントローラに知らせるINFを飛ばす
  const byte deoj[] = { 0x05, 0xFF, 0x01 };
  const byte edt[] = { 0x01, 0x31 };
  echo.sendMultiOPC1(deoj, EL_INF, 0x80, edt);
}



//====================================================================
// main loop
void loop() {

  //Serial.println(FANPOWER );
  echo.recvProcess();
  delay(200);
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