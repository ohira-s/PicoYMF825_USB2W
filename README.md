[日本語版READMEへ / README in Japanese](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/README_Jp.md)  
# Pico YMF825 USB MIDI
Pico YMF825 USB MIDI with Raspberry Pi PICO2W.  YMF825 is a synthesizer module as below.  

* 4 Operators / 7 algorithms FM sounds.
* 16 polyphonic voices.
* 3 BiQuad filters.

Pico YMF825 USB MIDI has sound parameter editor and MIDI-IN via USB.  
This device works as a USB host or a USB device.  

* As a USB host, you can connect a MIDI controller like a MIDI keyboard to this device.
* As a USB device, you can connect this device to a PC which any DAW application is working.  

Pico YMF825 USB MIDI Overview:  
![PICO YMF825 Overview](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/PicoYMF825_PKG_Overview.jpg)  

Pico YMF825 USB MIDI Compornents:  
![PICO YMF825 Overview](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/pico_ymf825_overview.jpg)

PICO2W is programmed with circuit python.  

# User's Manual
[User's Manual in Japanese is here.](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/UsersManual_Jp.md)  
[User's Manual in English is here.](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/UsersManual.md)  

# Schematics
[Schematics is here.](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/PicoYMF825USB_sch.pdf)  

# Software Installation
1) Copy circuitpython (v9.2.1) into PICO2W.  
2) Copy all files below to PICO2W root.  

- PicoYMF825_USB2W.py  

	Copy as code.py.  

- lib folder.  
- SYNTH folder.  
