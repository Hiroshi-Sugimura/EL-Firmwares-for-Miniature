# Overview

このリポジトリではVersatile miniature IoT device set（Miniature IoT unit set + ESP32）をECHONET Liteデバイス化するファームウェアを配布しています。


**注意：本モジュールによるECHONET Lite通信規格上の保証はなく、SDKとしてもECHONET Liteの認証を受けておりません。
また、製品化の場合には各社・各自がECHONET Lite認証を取得する必要があります。**

# How to Use
プログラムの焼き込み方は言語ごとに違います


### MicroPython Version
詳細は以下のリンクから確認してください

  [HowtoUSE_MicroPython](docs/HowtoUSE_MicroPython.md)


### Arduino Version
  必用なライブラリをインストールして通常通りに焼いてください

### FirmV2　Compatible with 「Serial ESP Wi-Fi Configurator (Web Serial)」
FirmV2は一度プログラミングを焼き込むと、以下のWEBサイトからUSB経由でWi-Fi設定の変更と再接続ができます。
-Serial ESP Wi-Fi Configurator (Web Serial): https://www.sugi-lab.net/utility/Serial_ESP_Wi-Fi_Configrator.html

***注意：他のアプリケーションがminiature Unitと通信している場合は正常に動作しません。
miniature Unitと通信するアプリは必ず一つにしてください。***

## Relation URL

- IoTをミニチュアで学ぶ　～動いて分かるIoT～: https://miniature.sugi-lab.net/
- 神奈川工科大学　杉村研究室: https://www.sugi-lab.net/

# Environment
MicroPython版とArduino IDE版の2種類で実装しています

### MicroPython版
- ELPythonを内部で利用しています。
- このモジュールは今回配布しているフォルダ内にECHONTLitフォルダとして含まれています。下記のGitHubでも配布しています。

  https://github.com/Hiroshi-Sugimura/ELPython

### Arduino IDE版
- EL_dev_arduinoを内部で利用しています。
- このモジュールはArduino IDEのライブラリ管理から追加できますが、下記のGitHubでも配布しています。

  https://github.com/Hiroshi-Sugimura/EL_dev_arduino



# Objects and Properties

各モデルのフォルダに対応オブジェクトとプロパティのリストをPDFで紹介しています。


# Demonstration

- 本ソフトウェアはミニチュアのECHONET Liteデバイスとして動作します。
- 具体的にソフトウェアの動作確認は下記の様なソフトウェアで確認できます。
  - iPhone向けApp EL Controller: https://apps.apple.com/jp/app/el-controller/id6657960074
  - PLIS: https://plis.sugi-lab.net/
  - HEMSセンターのSDK: http://sh-center.org/


# meta data

## Authors

神奈川工科大学  工学部  電気電子情報工学科; Dept. of Electric and Electronics, Faculty of Engineering, Kanagawa Institute of Technology

杉村　博; SUGIMURA, Hiroshi

## thanks

- Thanks to Github users!

## License

Model別、バージョン別で変更する可能性がありますので、各ModelとVersionで配布されている具体的なソフトウェア内のLICENSEをご確認ください。
