# Pico YMF825 USB MIDI User's Manual

![PICO YMF825 Overview](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/splash.jpg)
## 1. Function
　Pico YMF825 USB MIDIはUSB MIDI is a YMF825 Synthesizer working as a USB device.  Specifications of YMF825 are below.    

* 16 voices polyphonic.
* 4 operators FM sound.
* 3 BiQuad filters.
* Audio output.
* Controlled via SPI
* Unfortunately YMF825 is a discontinued product.  I can't find even any dead stock in 2025.  

## 2. Overview
![PICO YMF825 Overview](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/PicoYMF825_PKG_Overview.jpg)

1) Rotary Encoders R1〜R8  
![8 Rotary Encoders](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/encoder_host.jpg)  

	You can edit synthesizer sound and save/load it with 8 rotary encoders.  
	Generally turn right to increment a value, and turn left to decrement a value.  
	
2) Slide Switch  

	There is a slide switch on the right side of rotary encoders.  You can choose a USB mode (HOST or DEVICE mode) with it when Pico YMF825 USB MIDI is turning on.  
	
3) OLED Display  
![OLED Display](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_general.jpg)  

	Shows you various information.  
	
4) USB OTG Cable  

	You must use this cable when you choose USB HOST mode.  OTG cable supplies power (5V) and connects to a USB MIDI device like a MIDI keyboard.  
	
5) USB Cable  

	You must use this cable when you choose USB DEVICE mode.  This cable connects between PICO2W on board USB connector and USB HOST device like a PC with DAW application.  

## 3. CAUTION
　Never use both the USB OTG cable and the USB cable simultaneously.  Connected devices might be destroyed by a short circuit.  

## 4. Turn on with USB MIDI HOST mode
1) Prepare a Pico YMF825 USB MIDI.  
2) Set the slide switch on 8 Encoders to 0 (the bottom side).    
3) Prepare a USB MIDI controller like a MIDI keyboard which works in USB DEVICE mode.  
4) Connects the USB MIDI controller to the USB OTG signal cable.  
5) Connects the USB OTG power supply cable to an AC adaptor (5V).  
6) You will see "**PICO YMF825 USB SYN.**" on the OLED display.  This is a splash screen.  
7) LED for the slide switch turn on in red.  This color means a process searching a USB MIDI device.  A USB MIDI device is detected, the LED turn on in blue and you will see "**YMF825 GENERAL HOST**" on the display.  

※ Detecting a USB MIDI device.     
![Host Mode](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_general.jpg)  

## 5. Turn on with USB MIDI DEVICE mode
1) Prepare a Pico YMF825 USB MIDI.  
2) Prepare a USB MIDI HOST device like a PC with DAW application.  
3) Connect the PC and PICO2W with USB cable.  Use the USB port on PICO2W.    
4) Turn on the PC.  You will see "**PICO YMF825 USB SYN.**" on the Pico YMF825 USB's OLED display.  This is the splash screen.  
6) LED for the slide switch turn on in violet, and "**YMF825 GENERAL DEV**" on the OLED display.    

## 6. General Configurations
You will see the General Settings screen just after turn the device on.  In this screen, you can configure the overall parameters.  
![General Parameters](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_general.jpg)  

### 5-1. OLED display
|YMF825|GENERAL||HOST|
|----|-----|-----|----|
|OCTV:| 1|||
|ALGO:| 0:<1>*2|||
|LFO :| 2|||
||||
||||
||<1>-->2-->||
  
  
|Parameter|Functions|
|----|----|
|OCTV|Overall octave.|
|ALGO|4 operators algorithm.|
|LFO|LFO frequency.|
  
### 5-2. OCTV: R1
	Use the rotary encoder R1 to change the overall octave.  

|Value|Descriptions|
|----|----|
|0|The highest octave.|
|:|:|
|3|The lowest octave.|

### 5-2. ALGO: R2
	Use the rotary encoder R2 to choose an algorithm.  
	You will see a expression line "<1>*2" to show you operators' connections.  

|Notation|Descriptions|
|----|----|
|&lt;n&gt;|Operator n has a self-feedback feature.|
|m*n|Operator m modulates operator n.|
|m+n|Mixing operator m and n.|

	In addition, you can see an algorithm chart on the bottom of the OLED.  
	For instance, the expression for the algorithm 7 is as below.  
	<1>+2*3+4
	
	And the chart of it is as below.  
	<1>-----
	        +
	 2-->3--+-->
	        +
	 4------

|Value|Descriptions|
|----|----|
|0|Algorithm 0|
|:|:|
|7| Algorithm 7|

	The algorithms are as below.

|No.|Algorithm|
|----|----|
|0|<1>\*2|
|1|<1>+2|
|2|<1>+2+<3>+4|
|3|(<1>+2\*3)\*4|
|4|<1>\*2\*3\*4|
|5|<1>\*2+<3>\*4|
|6|<1>+2\*3\*4|
|7|<1>+2\*3+4|

### 5-3. LFO: R3
	Use the rotary encoder R2 to change the LFO frequency.  Vibrate and tremolo are affected by the LFO.

|Value|Descriptions|
|----|----|
|0|The lowest frequency.|
|:|:|
|7|The highest frequency.|

### 5-4. Change page: R8
	Use the rotary encoder R8 to move to next or previous page.  Turn right then next, left then previous page.  

## 6. Oscillator Configurations
You can configure the parameters for the operator's oscillation.  
![Oscillator Parameters](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_oscillator1.jpg)  

### 6-1. OLED display
|OSCL|[1]|2|3|4|
|----|-----|-----|----|----|
|WAVE:|0|0|0|0|
|FREQ:|2|4|4|4|
|DETU:|3|0|0|0|
|LEVL:|4|0|31|31|
|FDBK:|3|0|0|0|
|wav1:|...||||
|wav2:|...||||
|wav3:|...||||
|wav4:|...||||
|ALGO:|...||||
  
|Parameter|Descriptions|Note|
|----|----|----|
|WAVE|Choose a wave form.|6-2|
|FREQ|Choose a frequency.||
|DETU|Choose a detune.||
|LEVL|Choose a output level.||
|FDBK|Choose a feedback level.||
|wav1〜4|The wave form name for each operator.|6-2|
|ALGO|The current algorithm.|5-2|

	You can see 4 operators' configurations on the same screen.  However you can edit them for only one operator with showing as "[op]".  
	You can move to the other operator with turning the rotary encoder R8.  The operator2 mode is as below.    
![Operator2](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_oscillator2.jpg)  

|OSCL|1|[2]|3|4|
|----|-----|-----|----|----|
|WAVE:|0|0|0|0|
|FREQ:|2|4|4|4|
|DETU:|3|0|0|0|
|LEVL:|4|0|31|31|
|FDBK:|3|0|0|0|
|wav1:|...||||
|wav2:|...||||
|wav3:|...||||
|wav4:|...||||
|ALGO:|...||||

### 6-2. WAVE: R1
	Use the rotary encoder R1.  
	You can see a wave number in the WAVE, and its name in the wav.  The reference table for the wave number and its name as below.  

|WAVE|Name|WAVE|Name|
|----|----|----|----|
|0|SIN(t)|16|TRIANGLE(t)|
|1|plus(SIN(t))|17|plus(TRIANGLE(t))|
|2|abs(SIN(t))|18|abs(TRIANGLE(t))|
|3|SAIL(t)*2|19|absTRIh|
|4|SIN(2t)|20|TRIANGLE(2t)|
|5|abs(SIN(2t))|21|abs(TRIANGLE(2t))|
|6|SQUARE(t)|22|plus(SQUARE(2t))|
|7|RIBBON(t)|23|---|
|8|compress(SIGN(t))|24|SAW(t)|
|9|plus(comp(SIGN(t)))|25|plus(SAW(t))|
|10|abs(comp(SIGN(t)))|26|abs(SAW(t))|
|11|comp(SAIL(t))|27|abs(comp(SAW(t)))|
|12|comp(SIGN(2t))|28|SAW(2t)|
|13|plus(SIGN(2t))|29|abs(SAW(2t))|
|14|plus(SQUARE(t))|30|SQUARE(t)/4|
|15|---|31|---|

### 6-3. FREQ: R2
	Use the rotary encoder R2.  

|Value|Descriptions|
|----|----|
|0|The lowest frequency.|
|:|:|
|15|The highest frequency.|

### 6-4. DETU: R3
	Use the rotary encoder R3.  

|Value|Descriptions|
|----|----|
|0|No effect.|
|1|The minimum detune.|
|:|:|
|7|The maximum detune.|

### 6-5. LEVL: R4
	Use the rotary encoder R4.  

|Value|Descriptions|
|----|----|
|0|The maximum output level.|
|:|:|
|31|The minimum output level.|

### 6-6. FDBK: R5
	Use the rotary encoder R5.  

|Value|Descriptions|
|----|----|
|0|The minimum feedback level.|
|:|:|
|7|The maximum feedback level.|

### 6-7. Change page: R8
	Use the rotary encoder R8 to move to next or previous page.  Turn right then next, left then previous page.  

## 7. Envelope Configurations
You can configure the parameters for the operator's envelope (ADSSR).  
![Envelope Parameters](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_adssr.jpg)  

### 7-1. OLED display
|ADSR|[1]|2|3|4|
|----|-----|-----|----|----|
|ATCK:|0|0|0|0|
|DECY:|2|4|4|4|
|SUSL:|3|0|0|0|
|SUSR:|4|0|31|31|
|RELS:|3|0|0|0|
||||||
||||||
|ALGO:|...||||

	You can see 4 operators' configurations on the same screen.  However you can edit them for only one operator with showing as "[op]".  
	You can move to the other operator with turning the rotary encoder R8.  The operator2 mode is as below.    

|ADSR|1|[2]|3|4|
|----|-----|-----|----|----|
|ATCK:|0|0|0|0|
|DECY:|2|4|4|4|
|SUSL:|3|0|0|0|
|SUSR:|4|0|31|31|
|RELS:|3|0|0|0|
||||||
||||||
|ALGO:|...||||

### 7-2. ATCK: R1
	Use the rotary encoder R1 to choose a attack rate.  

|Value|Descriptions|
|----|----|
|0|No sound.|
|1|The maximum attack time.|
|:|:|
|14|The minimum attack time.|
|15|Sound immediately.|

### 7-3. DECY: R2
	Use the rotary encoder R2 to choose a decay rate.  

|Value|Descriptions|
|----|----|
|0|Never decay.|
|1|The maximum decay time.|
|:|:|
|14|The minimum decay time.|
|15|Decay immediately.|

### 7-4. SUSL: R3
	Use the rotary encoder R3 to choose a sustain level.  

|Value|Descriptions|
|----|----|
|0|The maximum level.|
|:|:|
|14|The minimum level.|
|15|Stop sound immediately.|

### 7-5. SUSR: R4
	Use the rotary encoder R4 to choose a sustain rate.  

|Value|Descriptions|
|----|----|
|0|Never decay.|
|1|The maximum decay time.|
|:|:|
|14|The minimum decay time.|
|15|Decay immediately.|

### 7-6. RELS: R5
	Use the rotary encoder R5 to choose a release rate.  

|Value|Descriptions|
|----|----|
|0|Never decay.|
|1|The maximum decay time.|
|:|:|
|14|The minimum decay time.|
|15|Decay immediately.|

### 7-7. Change page: R8
	Use the rotary encoder R8 to move to next or previous page.  Turn right then next, left then previous page.  

## 8. Modulation Configurations
You can configure the parameters for the operator's modulations.  
![Modulation Parameters](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_modulation.jpg)  

### 8-1. OLED display
|MODL|[1]|2|3|4|
|----|-----|-----|----|----|
|VIBE:|ON|ON|OFF|OFF|
|VIBD:|3|1|0|0|
|AMPE:|OFF|ON|OFF|OFF|
|AMPM:|0|4|0|0|
|KYSE:|OFF|OFF|OFF|OFF|
|KSLV:|0|0|0|0|
|IGOF:|OFF|OFF|ON|ON|
|ALGO:|...||||

	You can see 4 operators' configurations on the same screen.  However you can edit them for only one operator with showing as "[op]".  
	You can move to the other operator with turning the rotary encoder R8.  The operator2 mode is as below.    

|MODL|1|[2]|3|4|
|----|-----|-----|----|----|
|VIBE:|ON|ON|OFF|OFF|
|VIBD:|3|1|0|0|
|AMPE:|OFF|ON|OFF|OFF|
|AMPM:|0|4|0|0|
|KYSE:|OFF|OFF|OFF|OFF|
|KSLV:|0|0|0|0|
|IGOF:|OFF|OFF|ON|ON|
|ALGO:|...||||

### 8-2. VIBE: R1
	Use the rotary encoder R1 to choose a vibrate enable.  

|Value|Descriptions|
|----|----|
|OFF|Disabled.|
|ON|Enabled.|

### 8-3. VIBD: R2
	Use the rotary encoder R2 to choose a vibrate depth.  

|Value|Descriptions|
|----|----|
|0|The minimum depth.|
|:|:|
|3|The maximum depth.|

### 8-4. AMPE: R3
	Use the rotary encoder R3 to choose a tremolo enable.  

|Value|Descriptions|
|----|----|
|OFF|Disabled.|
|ON|Enabled.|

### 8-5. AMPM: R4
	Use the rotary encoder R4 to choose a tremolo depth.  

|Value|Descriptions|
|----|----|
|0|The minimum depth.|
|:|:|
|3|The maximum depth.|

### 8-6. KYSE: R5
	Use the rotary encoder R5 to choose a key sensitivity enable.  

|Value|Descriptions|
|----|----|
|OFF|Disabled.|
|ON|Enabled.|

### 8-7. KYLV: R6
	Use the rotary encoder R6 to choose a key sensitivity depth.  

|Value|Descriptions|
|----|----|
|0|The minimum depth.|
|:|:|
|3|The maximum depth.|

### 8-8. IGOF: R7
	Use the rotary encoder R6 to choose an ignore key off mode.  
	In the mode is OFF, the MIDI Note Off event starts the release time in ADSSR.  In the other hand, the MIDI Note Off event is ignored in the mode if ON.  

|Value|Descriptions|
|----|----|
|OFF|Disabled.|
|ON|Enabled.|

### 8-9. Change page: R8
	Use the rotary encoder R8 to move to next or previous page.  Turn right then next, left then previous page.  

## 9. Equalizer Configurations
You can configure the parameters for the 3 BiQuad equalizers.  
![Equalizer Parameters](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_equalizer1.jpg)  

### 9-1. OLED display
|EQLZ|[1]|
|----|-----|
|TYPE:|LPF|
|FREQ:|2.4000|
|Qfct:|0.8000|
|<-->:|&nbsp;&nbsp;&nbsp;^|

	You can see only one equalizer's configurations on a screen.  You can move to the other equalizer with turning the rotary encoder R8.  The equalizer 2 is as below.    
![Equalizer2](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/edit_equalizer2.jpg)  

|EQLZ|[2]|
|----|-----|
|TYPE:|ALL PASS|
|FREQ:|4.8000|
|Qfct:|0.1000|
|<-->:|^|

### 9-2. TYPE: R1
	Use the rotary encoder R1 to choose a filter type.  

|Value|Descriptions|
|----|----|
|ALL PASS|All pas filter.|
|LPF|Low path filter.|
|HPF|High path filter.|
|BPF:skirt|Band pass filter (skirt type).|
|BPF:0db|Band pass filter (0db type).|
|NOTCH|Notch filer.|

### 9-3. FREQ: R2
	Use the rotary encoder R2 to choose a filter cutoff frequency.  
	You can change a digit to edit with R4 cursor rotary encoder.  

### 9-4. Qfct: R3
	Use the rotary encoder R3 to choose a filter cutoff frequency.  
	You can change a digit to edit with R4 cursor rotary encoder.  

### 9-4. <-->: R4
	Use the rotary encoder R4 to change a digit to edit for FREQ and Qfct.  

### 9-5. Change page: R8
	Use the rotary encoder R8 to move to next or previous page.  Turn right then next, left then previous page.  

## 10. Save Sound Parameters
You can save the current parameters to PICO2W memory.  

### 10-1. OLED display
![Save Sound](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/save_sound.jpg)  

|SAVE|SOUND FILE|
|----|-----|
|BANK:|0|
|NUM.:|105:Sitar|
|NAME:|Sitar_NEW|
|<-->:|&nbsp;&nbsp;&nbsp;^|
|SAVE:|----|

### 10-2. TYPE: R1
	Use the rotary encoder R1 to choose a bank number to save.  

|Value|Descriptions|
|----|----|
|0|The 0th bank.|
|:|:|
|9|The 9th bank.|

### 10-3. NUM.: R2
	Use the rotary encoder R2 to choose a file number to save.  
	You can change a digit to edit with R4 cursor rotary encoder.  

|Value|Descriptions|
|----|----|
|000|The 0th file.|
|:|:|
|999|The 999th file.|

	You will see a file name is on the number automatically if the file exits, otherwise "<NEW FILE>".

### 10-3. NAME: R3
	Use the rotary encoder R3 to edit the file name.  
	You can change a character to edit with R4 cursor rotary encoder.  

### 10-5. <-->: R4
	Use the rotary encoder R4 to change a digit or a character to edit for NUM. and NAME.  

### 10-6. SAVE: R5
	Use the rotary encoder R5 to save the current parameters to the file.  

|Value|Descriptions|
|----|----|
|----|No effect (default position).|
|Save?|Confirm to save.|
|SAVE|Saving.|

### 10-7. Change page: R8
	Use the rotary encoder R8 to move to next or previous page.  Turn right then next, left then previous page.  

## 11. Load Sound Parameters
You can load a sound parameters' file from PICO2W memory.  

### 11-1. OLED display
![Load Sound](https://github.com/ohira-s/PicoYMF825_USB2W/blob/master/Docs/load_sound.jpg)  

|LOAD|SOUND FILE|
|----|-----|
|BANK:|0|
|NUM.:|105:Sitar|
|NAME:|itar|
|<-->:|&nbsp;&nbsp;^|
|LOAD:|----|

### 11-2. TYPE: R1
	Use the rotary encoder R1 to choose a bank number to load.  

|Value|Descriptions|
|----|----|
|0|The 0th bank.|
|:|:|
|9|The 9th bank.|

### 11-3. NUM.: R2
	Use the rotary encoder R2 to choose a file number to load.  
	You can find the existing files.  Moreover if you enter a search word in NAME, you can find only matched files.

|Value|Descriptions|
|----|----|
|000|The 0th file.|
|:|:|
|999|The 999th file.|

### 11-4. NAME: R3
	Use the rotary encoder R3 to edit the search word in sound names.  It is valid that the search word has more than 2 characters.
	You can change a character to edit with R4 cursor rotary encoder.  

### 11-5. <-->: R4
	Use the rotary encoder R4 to change a character to edit for NAME.  

### 11-6. LOAD: R5
	Use the rotary encoder R5 to save the current parameters to the file, or search sound files.  
	Turn right to load a sound parameter file.  
	Turn left to search sound parameter files.  

|Value|Descriptions|
|----|----|
|SEARCH|Searching.|
|Search?|Confirm to search.|
|----|No effect (default position).|
|Load?|Confirm to load.|
|LOAD|Loading.|

### 11-7. Change page: R8
	Use the rotary encoder R8 to move to next or previous page.  Turn right then next, left then previous page.  

