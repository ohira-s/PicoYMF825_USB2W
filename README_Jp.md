[英語版READMEへ / README in English](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/README.md)  
# Pico YMF825 USB MIDI
Pico YMF825 USB MIDIはRaspberry Pi PICO2Wで制御されたシンセサイザーです。YMF825は以下の仕様のシンセサイザーモジュールです。  

* 4オペレーター／7アルゴリズムFM音源
* 16音ポリフォニック
* 3段直列のBiQuadフィルター

Pico YMF825 USB MIDIは音色エディターとMIDI INの機能を持っていて、USBホストまたはデバイスとして動作させることができます。    

* USBホストモードでは、MIDIキーボードのようなコントローラーを接続して演奏できます。
* USBデバイスモードでは、DAWアプリが動くPCなどを接続してシーケンサーでの演奏などができます。   

Pico YMF825 USB MIDI外観（ケース格納前）:  
![PICO YMF825 Overview](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/pico_ymf825_overview.jpg)

PICO2Wはcircuit pythonでプログラムされています。  

# User's Manual
[日本語版はこちら](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/UsersManual_Jp.md)  
[User's Manual in English is under construction.]()  

# Software Installation
1) circuitpython (v9.2.1)をPICO2Wにコピーします。  
2) 以下のファイルをPICO2Wのルートにコピーします。  

- PicoYMF825_USB2W.py  

	code.pyとしてコピーします。  

- libフォルダー  
- SYNTHフォルダー  
