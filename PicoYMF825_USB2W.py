############################################################################
# USB MIDI Guitar and Drum Controler with Raspberry Pi PICO2 (USB DEVICE)
# FUNCTION:
#   A YMF825 4 operators FM synthesizer as a USB MIDI host device.
#
# HARDWARE:
#   CONTROLER  : Raspberry Pi PICO2/2W.
#                Additional USB works as a USB-MIDI host and power supply
#                via USB-OTG cable.
#                On board USB works as a USB-MIDI device and PC connection.
#   SYNTHESIZER: YMF825, 16 polyphonic voices with 4 operators FM sound.
#   OLED       : SH1107 (128x128) as a display.
#   INPUT      : 8 rotary encoders for M5Stack (8Encoder)
#
# PROGRAM: circuitpython (V9.2.1)
#   PicoYMF825_USB2W.py (USB host mode)
#     Copyright (c) Shunsuke Ohira
#     0.0.1: 04/19/2025
#            Play YMF825 via USB MIDI.
#            YMF825 operators editor.
#            YMF825 equalizers editor.
#
#     0.0.2: 04/20/2025
#            Save and Load parameter file.
#
#     0.0.3: 04/21/2025
#            Sound file filter.
#            Algorithm chart.
#            LED signs for assistancing user.
#
#     0.0.4: 04/22/2025
#            Improve the note off event (Voice unit aging).
#
# SPI:: YMF825
#   SCK: GP18(24)
#   TX : GP19(25) (MOSI)
#   RX : GP16(21) (MISO)
#   CS : GP17(22)
#
# Digital Out:: YMF825
#   RST: GP22(29)
#
# I2C Unit-0:: OLED
#   SDA: GP8(11)
#   SCL: GP9(12)
#
# I2C Unit-1:: 8Encoder (I2C Address = 0x41)
#   SDA: GP6( 9)
#   SCL: GP7(10)
#
# OLED SH1107 128x128
#   21 chars x 11 lines
#
# USB:: USB MIDI HOST
#   D+ : GP26(31)
#   D- : GP27(32)
############################################################################
import microcontroller		# CPU clock up

import asyncio
#import keypad

from board import *
import digitalio
import busio
from adafruit_bus_device.i2c_device import I2CDevice
from time import sleep
import json

from i2cdisplaybus import I2CDisplayBus
import displayio
import terminalio
import adafruit_display_text
from adafruit_display_text import label
import adafruit_displayio_sh1107

import usb_midi					# for USB MIDI
import adafruit_midi
#from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
#from adafruit_midi.pitch_bend import PitchBend
#from adafruit_midi.program_change import ProgramChange
import usb_host					# for USB HOST
import usb.core
from adafruit_usb_host_midi.adafruit_usb_host_midi import MIDI	# for USB MIDI HOST

import board
import supervisor
import math
import os

##########################################
# Get 8encoder status in async task
##########################################
async def get_8encoder():
    while True:
        Encoder_obj.i2c_lock()
        on_change = False
        
        try:
            enc_switch  = Encoder_obj.get_switch()
            change = (M5Stack_8Encoder_class.status['switch'] != enc_switch)
            on_change = on_change or change
            M5Stack_8Encoder_class.status['on_change']['switch'] = change
            M5Stack_8Encoder_class.status['switch'] = enc_switch
            await asyncio.sleep(0.02)
            
            for rt in list(range(8)):
                enc_rotary = Encoder_obj.get_rotary_increment(rt)
                change = (enc_rotary != 0)
                on_change = on_change or change
                M5Stack_8Encoder_class.status['on_change']['rotary_inc'][rt] = change
                M5Stack_8Encoder_class.status['rotary_inc'][rt] = enc_rotary
                await asyncio.sleep(0.02)
    
            Encoder_obj.i2c_unlock()

            if on_change:
                Application.task_8encoder()
        
        finally:
            Encoder_obj.i2c_unlock()

        # Gives away process time to the other tasks.
        # If there is no task, let give back process time to me.
        await asyncio.sleep(0.02)

##########################################
# MIDI IN in async task
##########################################
async def midi_in():
    while True:
        midi_msg = MIDI_obj.midi_in()
        if midi_msg is not None:
#            print('===>MIDI IN:', midi_msg)
            if isinstance(midi_msg, NoteOn):
#                print('NOTE ON :', midi_msg.note, midi_msg.velocity)
                YMF825_obj.note_on(midi_msg.note, midi_msg.velocity)

            elif isinstance(midi_msg, NoteOff):
#                print('NOTE OFF:', midi_msg.note)
                YMF825_obj.note_off(midi_msg.note)
                
        # Gives away process time to the other tasks.
        # If there is no task, let give back process time to me.
        await asyncio.sleep(0.0)

##########################################
# Asyncronous functions
##########################################
async def main():
    interrupt_get_8encoder = asyncio.create_task(get_8encoder())
    interrupt_midi_in      = asyncio.create_task(midi_in())
  
    await asyncio.gather(interrupt_get_8encoder, interrupt_midi_in)


###################################
# CLASS: USB MIDI
###################################
class MIDI_class:
    # Constructor
    #   USB MIDI
    #     usb_midi_host_port: A tuple of (D+, D-)
    def __init__(self, usb_midi_host_port=(GP26, GP27)):
        # USB MIDI device
        print('USB MIDI:', usb_midi.ports)
        self._usb_midi = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], midi_out=usb_midi.ports[1], out_channel=0)

        self._init = True
        self._raw_midi_host  = None
        self._usb_midi_host  = None
        self._usb_host_mode  = True
        self._midi_in_usb    = True			# True: MIDI-IN via USB, False: via UART1
        print('USB PORTS:', usb_midi.ports)
        
        # USB MIDI HOST port
#        h = usb_host.Port(board.USB_HOST_DP, board.USB_HOST_DM)
        h = usb_host.Port(usb_midi_host_port[0], usb_midi_host_port[1])

        if supervisor.runtime.usb_connected:
            print("USB<host>!")
        else:
            print("!USB<host>")

    # Is host mode or not
    def as_host(self):
        return self._usb_host_mode
    
    # Look for USB MIDI device
    def look_for_usb_midi_device(self):
        self._raw_midi_host = None
        self._usb_midi_host = None

        if self._init:
            print("Looking for midi device")

        try_count = 5000
#        while self._raw_midi_host is None and try_count > 0:
        Encoder_obj.i2c_lock()
        Encoder_obj.led(8, [0xff, 0x00, 0x00])
        sleep(1.0)
        while self._raw_midi_host is None and Encoder_obj.get_switch() == 0:

            try_count = try_count - 1
            devices_found = usb.core.find(find_all=True)

            if self._init:
                print('USB LIST:', devices_found)

            for device in devices_found:
                if self._init:
                    print('DEVICE: ', device)
                
                try:
                    if self._init:
                        print("Found", hex(device.idVendor), hex(device.idProduct))

#                    self._raw_midi_host = MIDI(device)				# bloking mode
                    self._raw_midi_host = MIDI(device, 0.05)		# none-blocking mode
#                    self._raw_midi_host = MIDI(device, 0.1)		# none-blocking mode
                    if self._init:
                        print("CONNECT MIDI")

                except ValueError:
                    self._raw_midi_host = None
                    print('EXCEPTION')
                    continue

        # Turn on the 8th LED for USB HOST mode or DEVICE mode
        if self._init:
            # Device mode
            if self._raw_midi_host is None:
                print('NOT Found USB MIDI device.')
                Encoder_obj.led(8, [0x80, 0x00, 0xff])
            
            # Host mode
            else:
                print('Found USB MIDI device.')
                Encoder_obj.led(8, [0x00, 0x80, 0xff])

        Encoder_obj.i2c_unlock()

        self._init = False
        if self._raw_midi_host is None:
            self._usb_midi_host = None
            self._usb_host_mode = False
            print('TURN ON WITH USB MIDI device mode.')
            return None
        
        self._usb_midi_host = adafruit_midi.MIDI(midi_in=self._raw_midi_host)  
#        self._usb_midi_host = adafruit_midi.MIDI(midi_in=self._raw_midi_host, in_channel=0)  
#        self._usb_midi = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0)
        print('TURN ON WITH USB MIDI HOST MODE.')
        return self._usb_midi_host
       
    # MIDI-IN via a port of the current mode
    def midi_in(self):            
        # MIDI-IN via USB
        if self._midi_in_usb:
            try:
                if self._usb_host_mode:
                    midi_msg = self._usb_midi_host.receive()
                else:
                    midi_msg = self._usb_midi.receive()

            except Exception as e:
                print('CHANGE TO DEVICE MODE:', e)
                Application_class.DISPLAY_TEXTS[0][4] = 'HOST' if MIDI_obj.as_host() else 'DEV'
                Application_class.DISPLAY_LABELS[0][4].text = Application_class.DISPLAY_TEXTS[0][4]
                Encoder_obj.i2c_lock()
                Encoder_obj.led(8, [0x80, 0x00, 0xff])
                Encoder_obj.i2c_unlock()

                self._usb_host_mode = False
                midi_msg = self._usb_midi.receive()
                
            return midi_msg

        return None

###################################
# CLASS: 8Encoder Unit for M5Stack
###################################
class M5Stack_8Encoder_class:
    status = {'switch': None, 'rotary_inc': [None]*8, 'on_change':{'switch': False, 'rotary_inc': [False]*8}}
    
    def __init__(self, scl=GP7, sda=GP6, i2c_address=0x41):
        self._i2c_address = i2c_address
        self._i2c = busio.I2C(scl, sda)			# board.I2C does NOT work for PICO, use busio.I2C
        self.i2c_lock()
        dev_hex = hex(i2c_address)
        devices = []
        while dev_hex not in devices:
            devices = [hex(device_address) for device_address in self._i2c.scan()]
            print("I2C addresses found:", devices)
            sleep(0.5)

        print('Found 8Encoder.')
        self.reset_rotary_value()
        for led in list(range(9)):
            self.led(8, [0x00, 0x00, 0x00])

        self.i2c_unlock()
    
    @staticmethod
    def __bits_to_int(val, bits):
        sign = 0x1 << (bits - 1)
        if val & sign != 0:
            exc = 2**bits - 1
            val = (val ^ exc) + 1
            return -val
            
        else:
            return int(val)


    def i2c_lock(self):
        while not self._i2c.try_lock():
            pass
    
    def i2c_unlock(self):
        self._i2c.unlock()

    def get_switch(self):
        bytes_read = bytearray(1)
        self._i2c.writeto(self._i2c_address, bytearray([0x60]))
        self._i2c.readfrom_into(self._i2c_address, bytes_read)
        sleep(0.01)
        return int(bytes_read[0])

    def reset_rotary_value(self, rotary=None):
        if rotary is None:
            for rt in list(range(8)):
                self._i2c.writeto(self._i2c_address, bytearray([0x40 + rt, 0x01]))
                sleep(0.01)

        else:
            self._i2c.writeto(self._i2c_address, bytearray([0x40 + rotary, 0x01]))

    def get_rotary_value(self, rotary):
        v = 0
        bytes_read = bytearray(1)
        base = 0x00 + rotary * 4
        for bs in list(range(3, -1, -1)):
            self._i2c.writeto(self._i2c_address, bytearray([base + bs]))
            self._i2c.readfrom_into(self._i2c_address, bytes_read)
            if rotary == 7:
                print('RET BYTES_READ:', bytes_read)
            v = (v << 8) | bytes_read[0]
            sleep(0.01)

        return M5Stack_8Encoder_class.__bits_to_int(v, 32)
    
    def get_rotary_increment(self, rotary):
        v = 0
        bytes_read = bytearray(4)
        base = 0x20 + rotary * 4
        shift = 0
#        for bs in list(range(3, -1, -1)):
        for bs in list(range(4)):
            self._i2c.writeto(self._i2c_address, bytearray([base + bs]))
            self._i2c.readfrom_into(self._i2c_address, bytes_read)
            v = v | (bytes_read[0] << shift)
            shift += 8
            sleep(0.01)

        return M5Stack_8Encoder_class.__bits_to_int(v, 32)

    # Turn on a LED in colro(R,G,B)
    def led(self, led_num, color=[0x00, 0x00, 0x00]):
        base = [0x70 + led_num * 3]
        self._i2c.writeto(self._i2c_address, bytearray(base + color))
        sleep(0.01)
        

###################################
# CLASS: OLED SH1107 128x128
###################################
class OLED_SH1107_128x128_class:
    def __init__(self, scl=GP9, sda=GP8, i2c_address=0x3c, WIDTH=128, HEIGHT=128):
        displayio.release_displays()
        self._BASE_Y = 36
        self._LINE_HEIGHT = 11
        self._FONT_WIDTH = 6

        self._screen = None

        self._i2c_address = i2c_address
        self._i2c = busio.I2C(scl, sda)			# board.I2C does NOT work for PICO, use busio.I2C
        self.i2c_lock()
        dev_hex = hex(i2c_address)
        devices = []
        while dev_hex not in devices:
            devices = [hex(device_address) for device_address in self._i2c.scan()]
            print("I2C addresses found:", devices)
            sleep(0.5)

        self._display_bus = I2CDisplayBus(self._i2c, device_address=self._i2c_address)
        print('Found OLED SH1107.')
        self.i2c_unlock()

        self._display = adafruit_displayio_sh1107.SH1107(self._display_bus, width=WIDTH, height=HEIGHT)
        print('SH1107 display generated.')

        # Draw test
        self._screen = self.make_screen()

        color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
        white_palette = displayio.Palette(1)
        white_palette[0] = 0xFFFFFF  # White
        black_palette = displayio.Palette(1)
        black_palette[0] = 0x000000  # Black

        bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=black_palette, x=0, y=0)
        self._screen.append(bg_sprite)
        print('Splash.')

        # Draw a smaller inner rectangle in black
#        BORDER = 2
#        inner_bitmap = displayio.Bitmap(WIDTH - BORDER * 2, HEIGHT - BORDER * 2, 1)
#        inner_palette = displayio.Palette(1)
#        inner_palette[0] = 0x000000  # Black
#        inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=BORDER, y=BORDER)
#        splash.append(inner_sprite)

        # Draw some white squares
#        small_bitmap = displayio.Bitmap(8, 8, 1)
#        small_square = displayio.TileGrid(small_bitmap, pixel_shader=white_palette, x=50, y=17)
#        splash.append(small_square)

        # Draw some label text3
##        text3 = "YMF825 USB MIDI HOST"  # overly long to see where it clips
##        text_area3 = self.new_label(text3, 0, 0)
##        self._screen.append(text_area3)

        # Draw some label text1
##        text1 = "CIRCUIT PYTHON567"  # overly long to see where it clips
##        text_area1 = self.new_label(text1, 1, 1)
##        self._screen.append(text_area1)

        # Draw some label text4
##        text4 = "01234567890123456789012"  # overly long to see where it clips
##        text_area4 = self.new_label(text4, 0, 2)
##        self._screen.append(text_area4)
        
        # Draw text lines
##        for t in list(range(3, 11)):
##            text_line = "L" + str(t)
##            self._screen.append(self.new_label(text_line, 0, t))
 
        # Draw the status bar on bottom
        small_bitmap = displayio.Bitmap(128, 7, 1)
        small_square = displayio.TileGrid(small_bitmap, pixel_shader=white_palette, x=0, y=25)
        self._screen.append(small_square)

    def i2c_lock(self):
        while not self._i2c.try_lock():
            pass
    
    def i2c_unlock(self):
        self._i2c.unlock()

    def screen(self):
        return self._screen

    def append_object(self, obj):
        self._screen.append(obj)

    def make_screen(self):
        screen = displayio.Group()
        self._display.root_group = screen
        return screen

    def new_label_xy(self, txt='', tx=0, ty=0, tcol=0xFFFFFF):
        return label.Label(terminalio.FONT, text=txt, color=tcol, x=tx, y=(self._BASE_Y + ty) % 128)

    def new_label(self, txt='', tx=0, ty=0, tcol=0xFFFFFF):
        return self.new_label_xy(txt, tx * self._FONT_WIDTH, ty * self._LINE_HEIGHT, tcol)


###################################
# CLASS: YMF825 FM Synthesizer
###################################
class YMF825_class:
    PARM_TEXT_OFF_ON = ["OFF", "ON "]
    PARM_TEXT_ALGO = [" 0:<1>*2", " 1:<1>+2", " 2:<1>+2+<3>+4", " 3:(<1>+2*3)*4", " 4:<1>*2*3*4", " 5:<1>*2+<3>*4", " 6:<1>+2*3*4", " 7:<1>+2*3+4"]
    ALOGOLITHM = [
        [	# 0|<1>*2
            '',
            '',
            '',
            '<1>-->2-->',
            '',
            '',
            ''
        ],
        [	# 1|<1>+2
            '',
            '',
            '<1>--',
            '     +-->',
            ' 2---',
            '',
            ''
        ],
        [	# 2|<1>+2+<3>+4
            '<1>--',
            '     +',
            ' 2---',
            '     +-->',
            '<3>--',
            '     +',
            ' 4---'
        ],
        [	# 3|(<1>+2*3)*4
            '',
            '',
            '<1>-----',
            '        +-->4',
            ' 2-->3--',
            '',
            ''
        ],
        [	# 4|<1>*2*3*4
            '',
            '',
            '',
            '<1>-->2-->3-->4',
            '',
            '',
            ''
        ],
        [	# 5|<1>*2+<3>*4
            '',
            '',
            '<1>-->2--',
            '         +-->',
            '<3>-->4--',
            '',
            ''
        ],
        [	# 6|<1>+2*3*4
            '',
            '<1>---------',
            '            +-->',
            ' 2-->3-->4--',
            '',
            '',
            ''
        ],
        [	# 7|<1>+2*3+4"]
            '',
            '<1>-----',
            '        +',
            ' 2-->3--+-->',
            '        +',
            ' 4------',
            ''
        ]
    ]
    PARM_TEXT_WAVE = [
        "SIN",     "plusSIN", "asbSIN",  "SAIL*2",
        "SIN2x",   "absSN2x", "SQUARE",  "RIBBON",
        "SINcomp", "plusScp", "absScmp", "SAILcmp",
        "SIN2xCp", "plsS2cp", "plusSQR", "-------",
        "TRIANGL", "plusTRI", "absTRIA", "absTRIh",
        "TRIAN2x", "plsTR2x", "plsSQR2", "-----",
        "SAW",     "plusSAW", "absSAW",  "absSAWc",
        "SAW2x",   "absSAW2", "SQUAR/4", "-------"
    ]
    PARM_TEXT_EQTYPE = ['ALL PASS', 'LPF', 'HPF', 'BPF:skart', 'BPF:0db', 'NOTCH']
    PARM_TEXT_SAVE = ['----', 'Sure?', 'SAVE', 'Sure?']
    PARM_TEXT_LOAD = ['----', 'Load?', 'LOAD', 'Load?', 'SEARCH', 'Search?']
    PARM_TEXT_CURSOR_F = ['^', ' ^', '   ^', '    ^', '     ^', '      ^']
    PARM_TEXT_CURSOR_T = ['^', ' ^', '  ^', '   ^', '    ^', '     ^', '      ^', '       ^']
    
    YMF825_PARM = {
        'GENERAL': [
            # Editor Page1
            # name, value_range 0..4-1, text_conversion, data_value
            # param_bytes[ 2]: NOP 000000 | Basic Octave 11
            {'name': "OCTV", 'max': 4, 'val_conv': '{:2d}',              'value': 1,             'parm_pos': 0, 'val_mask': 0x03, 'shift': 0, 'mask': 0x00},
            # param_bytes[ 3]:LFO 11 | NOP 000 | Algorithm 111
            {'name': "ALGO", 'max': 8, 'val_conv': PARM_TEXT_ALGO,    'value': 0,             'parm_pos': 1, 'val_mask': 0x07, 'shift': 0, 'mask': 0xf8},
            {'name': "LFO ", 'max': 8, 'val_conv': '{:2d}',              'value': 2,             'parm_pos': 1, 'val_mask': 0x03, 'shift': 6, 'mask': 0x07}
        ],
        
        # 4 OPERATORs
        'OPERATORS': [
            # name, value_range 0..4-1, text_conversion, data_value[0..3]
            
            # Editor Page2
            {'name': "WAVE", 'max': 32, 'val_conv': PARM_TEXT_WAVE,   'value': [ 0, 0, 0, 0], 'parm_pos':  8, 'val_mask': 0x1f, 'shift': 3, 'mask': 0x07},
            {'name': "FREQ", 'max': 16, 'val_conv': None,             'value': [ 2, 4, 4, 4], 'parm_pos':  7, 'val_mask': 0x0f, 'shift': 4, 'mask': 0x0f},
            {'name': "DETU", 'max':  8, 'val_conv': None,             'value': [ 3, 0, 0, 0], 'parm_pos':  7, 'val_mask': 0x0f, 'shift': 0, 'mask': 0xf0},
            {'name': "LEVL", 'max': 32, 'val_conv': None,             'value': [ 4, 0,31,31], 'parm_pos':  5, 'val_mask': 0x3f, 'shift': 2, 'mask': 0x03},
            {'name': "FDBK", 'max':  8, 'val_conv': None,             'value': [ 3, 0, 0, 0], 'parm_pos':  8, 'val_mask': 0x07, 'shift': 0, 'mask': 0xf8},

            # Editor Page3
            {'name': "ATCK", 'max': 16, 'val_conv': None,             'value': [14,14,14,14], 'parm_pos':  4, 'val_mask': 0x0f, 'shift': 4, 'mask': 0x0f},
            {'name': "DECY", 'max': 16, 'val_conv': None,             'value': [ 4, 4, 4, 4], 'parm_pos':  3, 'val_mask': 0x0f, 'shift': 0, 'mask': 0xf0},
            {'name': "SUSL", 'max': 16, 'val_conv': None,             'value': [12,12,12,12], 'parm_pos':  4, 'val_mask': 0x0f, 'shift': 0, 'mask': 0xf0},
            {'name': "SUSR", 'max': 16, 'val_conv': None,             'value': [ 7, 7, 7, 7], 'parm_pos':  2, 'val_mask': 0x0f, 'shift': 4, 'mask': 0x0f},
            {'name': "RELS", 'max': 16, 'val_conv': None,             'value': [ 5, 5, 5, 5], 'parm_pos':  3, 'val_mask': 0x0f, 'shift': 4, 'mask': 0x0f},

            # Editor Page4
            {'name': "VIBE", 'max':  2, 'val_conv': PARM_TEXT_OFF_ON, 'value': [ 0, 0, 0, 0], 'parm_pos':  6, 'val_mask': 0x01, 'shift': 0, 'mask': 0xfe},
            {'name': "VIBD", 'max':  4, 'val_conv': None,             'value': [ 0, 0, 0, 0], 'parm_pos':  6, 'val_mask': 0x07, 'shift': 1, 'mask': 0xf1},
            {'name': "AMPE", 'max':  2, 'val_conv': PARM_TEXT_OFF_ON, 'value': [ 0, 0, 0, 0], 'parm_pos':  6, 'val_mask': 0x01, 'shift': 4, 'mask': 0xef},
            {'name': "AMPM", 'max':  4, 'val_conv': None,             'value': [ 0, 0, 0, 0], 'parm_pos':  6, 'val_mask': 0x07, 'shift': 5, 'mask': 0x1f},
            {'name': "KYSE", 'max':  2, 'val_conv': PARM_TEXT_OFF_ON, 'value': [ 0, 0, 0, 0], 'parm_pos':  5, 'val_mask': 0x03, 'shift': 0, 'mask': 0xfc},
            {'name': "KSLV", 'max':  4, 'val_conv': None,             'value': [ 0, 0, 0, 0], 'parm_pos':  2, 'val_mask': 0x07, 'shift': 0, 'mask': 0xf8},
            {'name': "IGOF", 'max':  2, 'val_conv': PARM_TEXT_OFF_ON, 'value': [ 1, 1, 1, 1], 'parm_pos':  2, 'val_mask': 0x01, 'shift': 3, 'mask': 0xf7}
        ],
        
        'EQUALIZERS': [
            {'name': "TYPE", 'max':  6, 'val_conv': PARM_TEXT_EQTYPE,   'value': [    0,     0,     0], 'parm_pos': 8, 'val_mask': 0x1f, 'shift': 3, 'mask': 0x07},
            {'name': "FREQ", 'max': 48, 'val_conv': '{: =7.4f}',        'value': [4.096, 2.048, 8.000], 'parm_pos': 8, 'val_mask': 0x1f, 'shift': 3, 'mask': 0x07},
            {'name': "Qfct", 'max': 10, 'val_conv': '{: =7.4f}',        'value': [0.100, 0.540, 2.340], 'parm_pos': 8, 'val_mask': 0x1f, 'shift': 3, 'mask': 0x07},
            {'name': "NPOS", 'max':  6, 'val_conv': PARM_TEXT_CURSOR_F, 'value': [    1,     1,     1], 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00}
        ],
        
        'SAVE': [
            {'name': "BANK", 'max':   10, 'val_conv': '{:3d}',            'value':          9, 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00},
            {'name': "NUM.", 'max': 1000, 'val_conv': '{:03d}',           'value':          0, 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00},
            {'name': "NAME", 'max':    8, 'val_conv': '{:s}',             'value': '        ', 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00},
            {'name': "NPOS", 'max':    8, 'val_conv': PARM_TEXT_CURSOR_T, 'value':          0, 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00},
            {'name': "SAVE", 'max':    4, 'val_conv': PARM_TEXT_SAVE,     'value':          0, 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00}
        ],
        
        'LOAD': [
            {'name': "BANK", 'max':   10, 'val_conv': '{:3d}',            'value':          9, 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00},
            {'name': "NUM.", 'max': 1000, 'val_conv': '{:s}',             'value':          0, 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00},
            {'name': "NAME", 'max':    8, 'val_conv': '{:s}',             'value': '        ', 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00},
            {'name': "NPOS", 'max':    8, 'val_conv': PARM_TEXT_CURSOR_T, 'value':          0, 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00},
            {'name': "LOAD", 'max':    6, 'val_conv': PARM_TEXT_LOAD,     'value':          0, 'parm_pos': 0, 'val_mask': 0x00, 'shift': 0, 'mask': 0x00}
        ]
    }

    # Note data HI
    NOTENUM_HI = (0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x18,0x18,0x18,0x18,0x18,0x20,0x20,0x20,0x20,0x28,0x11,0x11,0x19,0x19,0x19,0x19,0x19,0x21,0x21,0x21,0x21,0x29,0x12,0x12,0x1A,0x1A,0x1A,0x1A,0x1A,0x22,0x22,0x22,0x22,0x2A,0x13,0x13,0x1B,0x1B,0x1B,0x1B,0x1B,0x23,0x23,0x23,0x23,0x2B,0x14,0x14,0x1C,0x1C,0x1C,0x1C,0x1C,0x24,0x24,0x24,0x24,0x2C,0x15,0x15,0x1D,0x1D,0x1D,0x1D,0x1D,0x25,0x25,0x25,0x25,0x2D,0x16,0x16,0x1E,0x1E,0x1E,0x1E,0x1E,0x26,0x26,0x26,0x26,0x2E,0x17,0x17,0x1F,0x1F,0x1F,0x1F,0x1F,0x27,0x27,0x27,0x27,0x2F,0x10,0x10,0x18,0x18,0x18,0x18,0x18,0x20,0x20,0x20,0x20,0x28,0x11,0x11,0x19,0x19,0x19,0x19,0x10,0x1E)
    # Note data LO
    NOTENUM_LO = (0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x65,0x5D)

    def __init__(self, spi_clock=GP18, spi_mosi=GP19, spi_miso=GP16, spi_cs=GP17, ymf825_reset=GP22):
        # YMF825 reset pin
        self._PIN_RESET = digitalio.DigitalInOut(ymf825_reset)
        self._PIN_RESET.direction = digitalio.Direction.OUTPUT
        
        # YMF825 SPI CS pin
        self._PIN_SPI_CS = digitalio.DigitalInOut(spi_cs)
        self._PIN_SPI_CS.direction = digitalio.Direction.OUTPUT
        
        # YMF825 SPI
        self._spi_locked = False
        self._spi = busio.SPI(spi_clock, MOSI=spi_mosi, MISO=spi_miso)			# board.SPI does NOT work for PICO, use busio.SPI
        self.spi_lock()
#        self._spi.configure(baudrate = 1000000, polarity = 0, phase = 0, bits = 8) 
#        self._spi.configure(baudrate = 7000000, polarity = 0, phase = 0, bits = 8) 
        self._spi.configure(baudrate = 10000000, polarity = 0, phase = 0, bits = 8) 
        self.spi_unlock()

        # Setup YMF825
        self.setup()

        # Voices
        self._voice_note = [None]*16
        self._voice_duration = [-1]*16
        
        # One equalizer parameters buffer (address + 15bytes)
        self.equalizer_ceq = bytearray(16)
        
        # Sound parameter files matched the search name in the current bank
        self.sound_files = []
        self.find_sound_files()

    def spi_lock(self):
        if self._spi_locked:
            return
        
        while not self._spi.try_lock():
            pass
        
        self._spi_locked = True

    def spi_unlock(self):
        if self._spi_locked:
            return
        
        self._spi.unlock()

    def spi_chip_select(self, select):
        self._PIN_SPI_CS.value = not select
        
    # Reset YMF825
    def reset(self):
        print("Reseting YMF825.")
        self._PIN_RESET.value = True
        sleep(1.0)
        self._PIN_RESET.value = False
        sleep(1.0)
        self._PIN_RESET.value = True
        sleep(1.0)
        print("Reset YMF825.")        

    # Write byte array data to SPI for YMF825
    #   addr:: SPI register address
    #   data_array: byte data in array
    def spi_write(self, addr, data_array):
        self.spi_lock()
        data_array[0] = addr
        self.spi_chip_select(True)
        self._spi.write(bytearray(data_array))
        self.spi_chip_select(False)
        self.spi_unlock()

    # Write one byte data to SPI for YMF825
    #   addr:: SPI register address
    #   byte_data: one byte data
    def spi_write_byte(self, addr, byte_data):
        self.spi_lock() 
        data_array = bytearray([addr, byte_data])
        self.spi_chip_select(True)
        self._spi.write(data_array)
        self.spi_chip_select(False)
        self.spi_unlock()

    # Get a parameter data with target and parameter name
    def get_value(self, target, parameter):
        if target in YMF825_class.YMF825_PARM:
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    return parm
        
        return None

    # Get a parameter value text to display
    def get_value_to_display(self, target, parameter, operator=0, as_wave_name=False):
        var = None
        frm = None
        if target == 'GENERAL':
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    val = parm['value']
                    frm = parm['val_conv']
                    break
            
        elif target == 'OPERATORS':
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    val = parm['value'][operator]
                    frm = parm['val_conv']
                    break
            
        elif target == 'EQUALIZERS':
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    val = parm['value'][operator]
                    frm = parm['val_conv']
                    break

        elif target == 'SAVE' or target == 'LOAD':
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    val = parm['value']
                    frm = parm['val_conv']

                    # Load file number
                    if target == 'LOAD' and parameter == 'NUM.':
                        print('LOAD NUM.:', val, self.sound_files[val])
                        val = self.sound_files[val]
                        
                    break

#        print('DISP:', target, parameter, val, frm)
        if val is not None:
            # Wave name
            if parameter == 'WAVE':
                # Return wave name as a string
                if as_wave_name:
                    return frm[val]
                
                # Return as a number
                ret = '{:3d}'.format(val)

            # format string is available
            elif frm is not None:
                # format() string
                if type(frm) == type(''):
                    ret = frm.format(val)
                
                # Assumed to be list [...]
                else:
                    ret = frm[val]

            # Default format
            else:
                ret = '{:3d}'.format(val)

            if target == 'OPERATORS' and operator < 3 and not as_wave_name:
                ret = ret + '|'
                
            return ret

    def increment_parameter_value(self, inc, target, parameter, operator=0):
#        print('INC_PARM:', inc, target, parameter, operator)
        if   target == 'GENERAL':
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    val = parm['value'] + inc
                    if val < 0:
                        val = parm['max'] - 1
                    elif val >= parm['max']:
                        val = 0
                        
                    parm['value'] = val
            
        elif target == 'OPERATORS':
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    val = parm['value'][operator] + inc
                    if val < 0:
                        val = parm['max'] - 1
                    elif val >= parm['max']:
                        val = 0
                        
                    parm['value'][operator] = val
            
        elif target == 'EQUALIZERS':
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    if   parameter == 'FREQ' or parameter == 'Qfct':
                        digit = self.get_value(target, 'NPOS')['value'][operator]
                        if digit <= 1:
                            val = parm['value'][operator] + inc * 10 ** (1 - digit)
                        else:
                            val = parm['value'][operator] + inc / 10 ** (digit - 1)

                        if val < 0:
                            val = parm['max']
                        elif val > parm['max']:
                            val = 0
                        
                    else:
                        val = parm['value'][operator] + inc
                        if val < 0:
                            val = parm['max'] - 1
                        elif val >= parm['max']:
                            val = 0
                        
                    parm['value'][operator] = val
                    
        elif target == 'SAVE' or target == 'LOAD':
            for parm in YMF825_class.YMF825_PARM[target]:
                if parm['name'] == parameter:
                    # Character data inc/dec
                    if parameter == 'NAME':
                        # Character position in the string
                        pos = self.get_value(target, 'NPOS')['value']
                        val = parm['value'][pos]
                        
                        if   inc > 0:
                            if val == '9':
                                val = ' '
                            elif val == ' ':
                                val = 'A'
                            elif val == 'Z':
                                val = 'a'
                            elif val == 'z':
                                val = '0'
                            else:
                                val = chr(ord(val) + 1)
                            
                        elif inc < 0:
                            if val == '0':
                                val = 'z'
                            elif val == 'a':
                                val = 'Z'
                            elif val == 'A':
                                val = ' '
                            elif val == ' ':
                                val = '9'
                            else:
                                val = chr(ord(val) - 1)
                        
                        val = parm['value'][:pos] + val + parm['value'][pos+1:]

                    # Find a next valid sound file
                    elif target == 'LOAD' and parameter == 'NUM.':
                        start = parm['value']
                        val = start + inc
                        if val < 0:
                            val = parm['max'] - 1
                        elif val >= parm['max']:
                            val = 0

                        skip = 0
                        while len(self.sound_files[val]) <= 4:
                            skip = skip + 1
                            val = val + inc
                            if val < 0:
                                val = parm['max'] - 1
                            elif val >= parm['max']:
                                val = 0
                                
                            if val == start:
                                break

                    # Default value inc/dec
                    else:
                        val = parm['value'] + inc
                        if val < 0:
                            val = parm['max'] - 1
                        elif val >= parm['max']:
                            val = 0
                        
                    parm['value'] = val
            
    def reverse_parameters(self, voice_params):
        params = self.YMF825_PARM['GENERAL']
        for prm in params:
            pos = prm['parm_pos']
            data_mask = prm['mask'] ^ 0xff
            mask = prm['mask']
            shift = prm['shift']
            
            valb = voice_params[pos] & data_mask
            value = valb >> shift
            value = value & mask
            print('GENERAL:' + prm['name'] + ' = ' + str(value))

        params = self.YMF825_PARM['OPERATORS']
        for opr in list(range(4)):
            for prm in params:
                pos = prm['parm_pos']
                data_mask = prm['mask'] ^ 0xff
                mask = prm['mask']
                shift = prm['shift']
                
                valb = voice_params[pos + opr + 7] & data_mask
                value = valb >> shift
                value = value & mask
                print('OPERATOR[' + str(opr) + ']: ' + prm['name'] + ' = ' + str(value))            

    # Save parameter file
    def save_parameter_file(self):
        # Save keys
        file_data = []
        for target in ['GENERAL', 'OPERATORS', 'EQUALIZERS', 'SAVE']:
            for parm in YMF825_class.YMF825_PARM[target]:
                print('save:', target, parm['name'], parm['value'])
                file_data.append({'target': target, 'name': parm['name'], 'value': parm['value']})

        parm = self.get_value('SAVE', 'BANK')
        if parm is None:
            return
        
        bank = parm['value']
        
        parm = self.get_value('SAVE', 'NUM.')
        if parm is None:
            return
        
        number = parm['value']
        print('SAVED:', file_data, str(bank), '{:03d}'.format(number))
        print('SAVE TO:', 'SYNTH/SOUND/SNDP' + str(bank) + '{:03d}'.format(number) + '.json')
        with open('SYNTH/SOUND/SNDP' + str(bank) + '{:03d}'.format(number) + '.json', 'w') as f:
            print('JSON.DUMP')
            json.dump(file_data, f)
            f.close()

    # Load parameter file
    def load_parameter_file(self):
        parm = self.get_value('LOAD', 'BANK')
        if parm is None:
            return
        
        bank = parm['value']
        
        parm = self.get_value('LOAD', 'NUM.')
        if parm is None:
            return
        
        number = parm['value']
        print('LOAD:', str(bank), '{:03d}'.format(number))
        print('LOAD FROM:', 'SYNTH/SOUND/SNDP' + str(bank) + '{:03d}'.format(number) + '.json')
        
        success = True
        try:
            with open('SYNTH/SOUND/SNDP' + str(bank) + '{:03d}'.format(number) + '.json', 'r') as f:
                file_data = json.load(f)
                print('LOADED:', file_data)
                f.close()
                
            for parm in file_data:
                target = parm['target']
                name = parm['name']
                value = parm['value']
                parameter = self.get_value(target, name)
                parameter['value'] = 0 if target == 'SAVE' and name == 'SAVE' else value
                
        except:
            success = False
        
        return success

    # Find sound files in the current bank and search name
    def find_sound_files(self):
        bank = self.get_value('LOAD', 'BANK')['value']
        name = self.get_value('LOAD', 'NAME')['value']
        name = name.strip()
#        print('SEARCH:', bank, name)
        
        # List all file numbers
        self.sound_files = []
        for filenum in list(range(1000)):
            self.sound_files.append('{:03d}:'.format(filenum))

        # Search files
        path_files = os.listdir('SYNTH/SOUND/')
        print('FILES:', path_files)
        for pf in path_files:
            print('FILE=', pf)
            if pf[-5:] == '.json':
                if pf[0:4] == 'SNDP':
                    bk = int(pf[4])
                    if bk == bank:
                        filenum = int(pf[5:8])
                        with open('SYNTH/SOUND/' + pf, 'r') as f:
                            file_data = json.load(f)
                            for parm in file_data:
                                if parm['target'] == 'SAVE' and parm['name'] == 'NAME':
                                    sound_name = parm['value']
#                                    print('SOUND NAME:', filenum, sound_name, name, sound_name.find(name))
                                    if len(name) <= 3 or sound_name.find(name) >= 0:
                                        self.sound_files[filenum] = self.sound_files[filenum] + sound_name
                                        
                            f.close()

        parm = self.get_value('LOAD', 'NUM.')
        parm['value'] = 0
        for filenum in list(range(1000)):
            if len(self.sound_files[filenum]) >= 5:
                parm['value'] = filenum
                break

    # Send the current parameter edited
    def send_parameters(self, voice_params):
        address_voices = bytearray([0x00,0x90])
        trailer = bytearray([0x80,0x03,0x81,0x80])
        sound_params = bytearray([])
        sound_params += address_voices
        for v in list(range(16)):
            sound_params += voice_params
            
        sound_params += trailer
#        print('SOUND PARAMETERS:', len(sound_params), sound_params)

        # Send data with burst mode
        self.spi_write_byte(0x08,0xF6)
#        sleep(0.2)
        self.spi_write_byte(0x08,0x00)
#        sleep(0.2)
        self.spi_write(0x07, sound_params)
        sleep(0.2)

    # Send the current sound parameter to YMF825
    def send_edited_sound_param(self):
        # General Parameters: 30bytes
        sound_param = bytearray(30)
        for param in YMF825_class.YMF825_PARM['GENERAL']:
            val        = param['value']
            byte_order = param['parm_pos']
            self_mask  = param['val_mask']
            shift_left = param['shift']
            data_mask  = param['mask']
            sound_param[byte_order] = (sound_param[byte_order] & data_mask) | ((val & self_mask) << shift_left)

        # Operators Parameters: OP1=[4]..[10] / OP2=[11]..[17] / OP3=[18]..[24] / OP4=[25]..[31]
        for opr in list(range(4)):
            for param in YMF825_class.YMF825_PARM['OPERATORS']:
                val        = param['value'][opr]
                byte_order = param['parm_pos'] + opr * 7
                self_mask  = param['val_mask']
                shift_left = param['shift']
                data_mask  = param['mask']
                sound_param[byte_order] = (sound_param[byte_order] & data_mask) | ((val & self_mask) << shift_left)

        # DEBUG: show parameters
#        print('PARAM:', hex(sound_param[0]), hex(sound_param[0]))
#        for op in list(range(4)):
#            bt = op * 7 + 2
#            print('  OP' + str(op) + ':', hex(sound_param[bt]), hex(sound_param[bt+1]), hex(sound_param[bt+2]), hex(sound_param[bt+3]), hex(sound_param[bt+4]), hex(sound_param[bt+5]), hex(sound_param[bt+6]))

        # Send sound parameters to YMF825
        self.send_parameters(sound_param)
        return

    # YMF825 setup
    def setup(self):
        # YMF825 chip hardware reset
        self.reset()

        self.spi_write_byte(0x1D,0x00)
        self.spi_write_byte(0x02,0x0E)
        sleep(0.2)
      
        self.spi_write_byte(0x00,0x01)
        self.spi_write_byte(0x01,0x00)
        self.spi_write_byte(0x1A,0xA3)
        sleep(0.2)
      
        self.spi_write_byte(0x1A,0x00)
        sleep(0.4)
      
        self.spi_write_byte(0x02,0x04)
        sleep(0.2)

        self.spi_write_byte(0x02,0x00)

        # add
        self.spi_write_byte(0x19,0xFF)
        self.spi_write_byte(0x1B,0x3F)
        self.spi_write_byte(0x14,0x00)
        self.spi_write_byte(0x03,0x01)

        self.spi_write_byte(0x08,0xF6)
        sleep(0.4)

        self.spi_write_byte(0x08,0x00)
        self.spi_write_byte(0x09,0xF8)
        self.spi_write_byte(0x0A,0x00)

        self.spi_write_byte(0x17,0x40)
        self.spi_write_byte(0x18,0x00)
        sleep(0.2)

        # Default sound
        voice_params = bytearray([
            0x01,0x85,
            0x00,0x7F,0xF4,0xBB,0x00,0x10,0x40,
            0x00,0xAF,0xA0,0x0E,0x03,0x10,0x40,
            0x00,0x2F,0xF3,0x9B,0x00,0x20,0x41,
            0x00,0xAF,0xA0,0x0E,0x01,0x10,0x40,
        ])

        self.send_parameters(voice_params)
        self.set_chanel()

#        self.reverse_parameters(voice_params)
        
#        self.spi_unlock()
        print("YMF825 initialized.")

    # Set Chanel
    def set_chanel(self):
        self.spi_write_byte(0x0F,0x30)
        self.spi_write_byte(0x10,0x71)
        self.spi_write_byte(0x11,0x00)
        self.spi_write_byte(0x12,0x08)
        self.spi_write_byte(0x13,0x00)
        sleep(0.2)

    def get_voice(self, notenum, note_on = True):
        # Vacant voice
#        print('GET VOICE:', notenum, note_on)
        voice = -1
        if note_on:
            voice = self._voice_note.index(None) if None in self._voice_note else -1

        # Same voice has been used
        off_voice = -1
        if notenum in self._voice_note:
            # Send note it off
            off_voice = self._voice_note.index(notenum)
            self._note_on(off_voice, YMF825_class.NOTENUM_HI[notenum], YMF825_class.NOTENUM_LO[notenum], 0)

            # Aging voice flag (-1)
            self._voice_note[off_voice] = -1
            self._voice_duration[off_voice] = 0
#            print('  --->OFF  VOICE:', off_voice, notenum)
            
        if not note_on:
#            print('<---NOTE OFF:', self._voice_note)
            return off_voice

        # Return the vacant voice
        if voice >= 0:
#            print('<---VAC VOICE:', voice)
            return voice
        
        # Find a voice having the maximum duration
        max_dur = -10
        for v in list(range(len(self._voice_note))):
            if self._voice_note[v] is not None:
                # Get the maximun duration voice in used voices
                dur = self._voice_duration[v]
                if dur > max_dur:
                    voice = v
                    max_dur = dur
                
                # Increment duration
                self._voice_duration[v] = self._voice_duration[v] + 1

        # Use an aging_voice if used voice is not available
#        print('MAX DURATION=', voice, self._voice_duration[voice], self._voice_note)
        if self._voice_note[voice] >= 0:
            # Note off the maximum duration note
            note = self._voice_note[voice]
            self._note_on(voice, YMF825_class.NOTENUM_HI[note], YMF825_class.NOTENUM_LO[note], 0)

        # Return maximum duration voice
        self._voice_note[voice] = None
        self._voice_duration[voice] = -1
#        print('<---MAX VOICE:', voice)
        return voice

    # voice: Voice number in YMF825 (0..15)
    # Note on with native values
    #   fnumh, fnuml:: 2byte data to play, byte data for a note is in notenum_hi[note] and notenum_lo[note]
    # Note on (play a note).
    # NOTICE:: Never call this directory, use play_by_scale() or play_by_timbre_scale().
    #   fnumh, fnuml:: 2byte data to play, byte data for a note is in notenum_hi[note] and notenum_lo[note].
    def _note_on(self, voice, notenum_h, notenum_l, velocity = 0x1c):
#        print("_NOTE:", 'OFF' if velocity == 0 else 'ON ', voice, notenum_h, notenum_l, velocity)
        # Send note on to YMF825
        # 0x40=Note ON / 0x00=Note OFF: b0NMEVVVV (N=Note ON/OFF, M=Mute, E=EG_REST, V=Voice)
        
        # Note ON
        if velocity != 0:
            self.spi_write_byte(0x0B, voice & 0x0f)
            self.spi_write_byte(0x0C, velocity & 0x7c)
            self.spi_write_byte(0x0D, notenum_h)
            self.spi_write_byte(0x0E, notenum_l)
            self.spi_write_byte(0x0F, 0x40 | (voice&0x0f))

        # Note OFF
        else:
            self.spi_write_byte(0x0F, voice&0x0f)

    # Note ON in vacant voice with MIDI note number (0..127)
    def note_on(self, notenum, velocity=0x1c):
        if velocity == 0:
            self.note_off(notenum)
            return
        
        voice = self.get_voice(notenum)
        if voice >= 0:
            notenum = notenum % 127
#            self._note_on(self.get_voice(notenum), YMF825_class.NOTENUM_HI[notenum], YMF825_class.NOTENUM_LO[notenum], velocity & 0x7c)
            self._note_on(voice, YMF825_class.NOTENUM_HI[notenum], YMF825_class.NOTENUM_LO[notenum], velocity & 0x7c)
            self._voice_note[voice] = notenum
            self._voice_duration[voice] = 0
#            print('<---NOTE ON:', self._voice_note)
            
#        else:
#            print('===NO VACANT VOICE==:', notenum, velocity)
#            print('NOTE ON:', notenum, velocity, '@', voice)
#            print('NOTE ON:', notenum, velocity, '@', voice, self._voice_note, self._voice_duration)
    
    # Note OFF with MIDI note number (0..127)
    def note_off(self, notenum):
        # Find the note and note it off (if available)
        self.get_voice(notenum, False)

    #Note off
    #  Turn off the note playing
    def all_note_off(self):
        self.spi_write_byte(0x0F,0x00)

    # Calculate the biquad filter parameters
    def calc_biquad_filter(self, filter_type, cutoff_freq, q_factor):
        # Calculate the filter parameters
        if q_factor < 0.01:
            q_factor = 0.01

    #    print("BIQUAD FILTER:{}, Fc={}, Q={}".format(flt_type, fc, qv))
        w0 = math.pi * 2 * cutoff_freq / 48.000
        alpha = math.sin(w0) / (q_factor + q_factor)
        cosw0 = math.cos(w0)
        a0 = 1.0 + alpha
        a1 = cosw0 * 2 / a0
        a2 = (alpha - 1.0) / a0

        filter_name = YMF825_class.PARM_TEXT_EQTYPE[filter_type]
        if filter_name == 'LPF':
            b0 = (1.0 - cosw0) / (a0 + a0)
            b1 = (1.0 - cosw0) / a0
            b2 = b0
            
        elif filter_name == 'HPF':
            b0 = (1.0 + cosw0) / (a0 + a0)
            b1 = -(1.0 + cosw0) / a0
            b2 = b0
            
        elif filter_name == 'BPF:skart':
            b0 = q_factor * alpha / a0
            b1 = 0
            b2 = -b0
            
        elif filter_name == 'BPF:0db':
            b0 = alpha / a0
            b1 = 0
            b2 = -b0
            
        elif filter_name == 'NOTCH':
            b0 = 1 / a0
            b1 = -2 * cosw0 / a0
            b2 = b0
            
        elif filter_name == 'ALL PASS':
            b0 = (1 - alpha) / a0
            b1 = -2 * cosw0 / a0
            b2 = (1 + alpha) / a0
            
        else:
    #        print("UNKNOWN FILTER TYPE.")
            return

        print('EQ:', filter_name, a0, a1, a2, b0, b1, b2)
        return {'a0': a0, 'a1': a1, 'a2': a2, 'b0': b0, 'b1': b1, 'b2': b2}

    def send_equalizer_parameters(self, eqno):

        # Floating point decoder
        def dec2bin_frac(dec, sign = False, digits=54):
#            dec=Decimal(str(dec))
            dec=float(str(dec))
            mantissa=''
            nth=0
            first=0
            rb=False
            while dec:
                if dec  >= 1:
#                    mantissa += '1'
                    mantissa += '1' if not sign else '0'
                    dec = dec -1
                    if first==0:
                        first=nth
                else:
                    if nth!=0:
#                        mantissa += '0'
                        mantissa += '0' if not sign else '1'
                    else:
                        mantissa += '0.'
                dec*=2
                nth+=1
                if nth-first==digits:
                    if dec != 0:
                        rb=True
                    break

            carry = False
            if sign:
#                print("SIGN BFR:", mantissa)
                revs = ""
                lman = len(mantissa)
                for b in range(1,lman-1):
                    if mantissa[-b] == "0":
                        revs = "1" + revs
                        if b != lman-2:
                            revs = mantissa[2:lman-b] + revs

                        break
                    else:
                        revs = "0" + revs
                        if b == lman-2:
                            carry = True

                mantissa = "0." + revs
#                print("SIGN AFT:", mantissa, carry)

            return mantissa,carry,rb

        # Make CEQ# bytes data
        def make_ceq_bytes(ceq_num, ceq):
            ceq_num = ceq_num * 3 + 1

            if ceq < 0.0:
                sign = True
                self.equalizer_ceq[ceq_num] = 0x80
                ceq = -ceq
                ceq_int = ( ~int(ceq) ) & 0x07
                ceq_frc = ceq - int(ceq)
            else:
                sign = False
                self.equalizer_ceq[ceq_num+1] = 0x00
                ceq_int = int(ceq) & 0x07
                ceq_frc = ceq - int(ceq)

            if ceq_frc != 0.0:
                mantissa,carry,rb = dec2bin_frac( ceq_frc, sign, 23 )
                if carry:
                    ceq_int += 1

#                print("EQUALIZER BITS and CARRY = INT:", mantissa, carry, "=", ceq_int)
                self.equalizer_ceq[ceq_num] = self.equalizer_ceq[ceq_num] | ( ceq_int << 4 )
#                print("FRC:: CEQ INT SHIFT ARRAY FRAC=", ceq, ceq_int, ( ceq_int << 4 ), self.equalizer_ceq[ceq_num], ceq_frc)
                for b in range(2,len( mantissa )):
#                    print("BIT:", b, "=", mantissa[b])
                    if mantissa[b] == "1":
                        if   b <=  5:       #  2.. 5
                            self.equalizer_ceq[ceq_num  ] = self.equalizer_ceq[ceq_num  ] | ( 0x01 << ( 5-b) )
                        elif b <= 13:       #  6..13
                            self.equalizer_ceq[ceq_num+1] = self.equalizer_ceq[ceq_num+1] | ( 0x01 << (13-b) )
                        elif b <= 21:       # 14..21
                            self.equalizer_ceq[ceq_num+2] = self.equalizer_ceq[ceq_num+2] | ( 0x01 << (21-b) )

            else:
                if sign:
                    ceq_int += 1

                self.equalizer_ceq[ceq_num] = self.equalizer_ceq[ceq_num] | ( ceq_int << 4 )
#                print("INT:: CEQ INT SHIFT ARRAY FRAC=", ceq, ceq_int, ( ceq_int << 4 ), self.equalizer_ceq[ceq_num], ceq_frc)

#            print("EQL::", self.equalizer_ceq[ceq_num], self.equalizer_ceq[ceq_num+1], self.equalizer_ceq[ceq_num+2])

        # Equalizer parameters buffer (address + 15bytes)
        self.equalizer_ceq = bytearray(16)
        equalizer = YMF825_class.YMF825_PARM['EQUALIZERS']
        filter_params = self.calc_biquad_filter(equalizer[0]['value'][eqno], equalizer[1]['value'][eqno], equalizer[2]['value'][eqno])
        print('EQ', eqno, filter_params)

        # Clear CEQ bytes data
        for b in range(15):
            self.equalizer_ceq[b] = 0x00

        # Make CEQ0 bytes data
        make_ceq_bytes(0, filter_params['b0'])
        make_ceq_bytes(1, filter_params['b1'])
        make_ceq_bytes(2, filter_params['b2'])
        make_ceq_bytes(3, filter_params['a1'])
        make_ceq_bytes(4, filter_params['a2'])

        #Burst write mode and all key notes off
        print("EQUALIZER", eqno, ":", self.equalizer_ceq)
        self.spi_write_byte(0x08, 0xF6)
        self.spi_write_byte(0x08, 0x00)
        self.spi_write(32 + eqno, self.equalizer_ceq)
        sleep(0.2)


###################################
# CLASS: Application
###################################
class Application_class:
    DISPLAY_TEXTS = []
    DISPLAY_LABELS = []
    DISPLAY_PAGE = 0
    DISPLAY_PAGE_FORMAT = [
        {'title': ['YMF825 GENERAL', '', '', '', '' ], 'target': 'GENERAL',    'range': ( 0, 2), 'unit': 0},

        {'title': ['OSCL:', '[1]', ' 2', ' 3', ' 4' ], 'target': 'OPERATORS',  'range': ( 0, 4), 'unit': 0},
        {'title': ['OSCL:', ' 1', '[2]', ' 3', ' 4' ], 'target': 'OPERATORS',  'range': ( 0, 4), 'unit': 1},
        {'title': ['OSCL:', ' 1', ' 2', '[3]', ' 4' ], 'target': 'OPERATORS',  'range': ( 0, 4), 'unit': 2},
        {'title': ['OSCL:', ' 1', ' 2', ' 3', '[4]' ], 'target': 'OPERATORS',  'range': ( 0, 4), 'unit': 3},
        
        {'title': ['ADSR:', '[1]', ' 2', ' 3', ' 4' ], 'target': 'OPERATORS',  'range': ( 5, 9), 'unit': 0},
        {'title': ['ADSR:', ' 1', '[2]', ' 3', ' 4' ], 'target': 'OPERATORS',  'range': ( 5, 9), 'unit': 1},
        {'title': ['ADSR:', ' 1', ' 2', '[3]', ' 4' ], 'target': 'OPERATORS',  'range': ( 5, 9), 'unit': 2},
        {'title': ['ADSR:', ' 1', ' 2', ' 3', '[4]' ], 'target': 'OPERATORS',  'range': ( 5, 9), 'unit': 3},
        
        {'title': ['MODL:', '[1]', ' 2', ' 3', ' 4' ], 'target': 'OPERATORS',  'range': (10,16), 'unit': 0},
        {'title': ['MODL:', ' 1', '[2]', ' 3', ' 4' ], 'target': 'OPERATORS',  'range': (10,16), 'unit': 1},
        {'title': ['MODL:', ' 1', ' 2', '[3]', ' 4' ], 'target': 'OPERATORS',  'range': (10,16), 'unit': 2},
        {'title': ['MODL:', ' 1', ' 2', ' 3', '[4]' ], 'target': 'OPERATORS',  'range': (10,16), 'unit': 3},
        
        {'title': ['EQLZ:', '[1]', '', '', ''       ], 'target': 'EQUALIZERS', 'range': ( 0, 3), 'unit': 0},
        {'title': ['EQLZ:', '[2]', '', '', ''       ], 'target': 'EQUALIZERS', 'range': ( 0, 3), 'unit': 1},
        {'title': ['EQLZ:', '[3]', '', '', ''       ], 'target': 'EQUALIZERS', 'range': ( 0, 3), 'unit': 2},
        
        {'title': ['SAVE SOUND FILE', '', '', '', ''], 'target': 'SAVE',       'range': ( 0, 4), 'unit': 0},
        {'title': ['LOAD SOUND FILE', '', '', '', ''], 'target': 'LOAD',       'range': ( 0, 4), 'unit': 0}
    ]
    
    DISPLAY_PAGE_MAX = len(DISPLAY_PAGE_FORMAT)
    LABEL_TO_DISPLAY = {}	# Bind data and display label with tuple: {(target, data name, unit) : label}
    
    def __init__(self):
        for row in list(range(11)):
            Application_class.DISPLAY_TEXTS.append([])
            Application_class.DISPLAY_LABELS.append([])
            for col in list(range(5)):
#                Application_class.DISPLAY_TEXTS[row].append(str(col) + str(row))
                Application_class.DISPLAY_TEXTS[row].append('')
                Application_class.DISPLAY_LABELS[row].append(None)

    # Set text on the display
    def set_text(self, row, col, str):
        Application_class.DISPLAY_TEXTS[row][col] = str
        Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]

    def splash_screen(self):
        self.set_text( 0, 0, '--------------------')
        self.set_text( 1, 0, 'PICO YMF825 USB SYN.')
        self.set_text( 2, 0, '--------------------')
        self.set_text( 3, 0, '4 OPs FM Synthesizer')
        self.set_text( 4, 0, '3 BiQuad Filters')
        self.set_text( 6, 0, 'copyright (c)')
        self.set_text( 7, 1, '2025, S.Ohira')
        self.set_text( 9, 0, 'Finding a MIDI dev..')
        self.set_text(10, 0, 'SW->1 for device mod')
        sleep(3.0)

    # Start display
    def start(self):
        for row in list(range(11)):
            for col in list(range(5)):
                label = OLED_obj.new_label(Application_class.DISPLAY_TEXTS[row][col], 0 if col == 0 else (col - 1) * 4 + 5, row)
                Application_class.DISPLAY_LABELS[row][col] = label
                OLED_obj.append_object(label)

        self.splash_screen()

    # Show a parameter on its label
    def show_parameter(self, target, parameter, operator=0):
        # Get bind data of data and dispaly label
        tpl = (target, parameter, operator)
        if tpl in Application_class.LABEL_TO_DISPLAY:
            row, col = Application_class.LABEL_TO_DISPLAY[tpl]
            Application_class.DISPLAY_TEXTS[row][col] = YMF825_obj.get_value_to_display(target, parameter, operator)
            Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]
            
            # Show wave name
            if parameter == 'WAVE':
                Application_class.DISPLAY_TEXTS[5 + col][1] = YMF825_obj.get_value_to_display(target, parameter, operator, True)
                Application_class.DISPLAY_LABELS[5 + col][1].text = Application_class.DISPLAY_TEXTS[5 + col][1]

    def show_algorithm_chart(self, row):
        for col in list(range(5)):
            Application_class.DISPLAY_TEXTS[row][col] = ''
            Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]

        algo = YMF825_obj.get_value('GENERAL', 'ALGO')['value']
        Application_class.DISPLAY_TEXTS[row][1] = YMF825_class.ALOGOLITHM[algo][row-4]
        Application_class.DISPLAY_LABELS[row][1].text = Application_class.DISPLAY_TEXTS[row][1]

    # Change the current page to edit
    def change_page(self):
        # Page format
#        print('Application Page:', Application_class.DISPLAY_PAGE)
        disp_frmt = Application_class.DISPLAY_PAGE_FORMAT[Application_class.DISPLAY_PAGE]
        
        # Parameters target and its range
        target = disp_frmt['target']
        parm = disp_frmt['range'][0]
        parm_last = disp_frmt['range'][1]
        unit = disp_frmt['unit']

        # Title on the top line on the display
        for col in list(range(4,-1,-1)):
            Application_class.DISPLAY_TEXTS[0][col] = disp_frmt['title'][col]
            Application_class.DISPLAY_LABELS[0][col].text = Application_class.DISPLAY_TEXTS[0][col]

        # WAVE has a special treatment
        show_wave_names = False

        # GENERAL parameter's page
        if   target == 'GENERAL':
            # Show USB MIDI mode
            Application_class.DISPLAY_TEXTS[0][4] = 'HOST' if MIDI_obj.as_host() else 'DEV'
            Application_class.DISPLAY_LABELS[0][4].text = Application_class.DISPLAY_TEXTS[0][4]
                                
            # Show each display line
            for row in list(range(1,11)):
                # Show parameter
                if parm <= parm_last:
                    # No data space
                    for col in list(range(2,5)):
                        Application_class.DISPLAY_TEXTS[row][col] = ''
                        Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]

                    # Parameter name
                    Application_class.DISPLAY_TEXTS[row][0] = YMF825_class.YMF825_PARM[target][parm]['name'] + ':'
                    Application_class.DISPLAY_LABELS[row][0].text = Application_class.DISPLAY_TEXTS[row][0]
 
                    # Parameter value
                    Application_class.DISPLAY_TEXTS[row][1] = YMF825_obj.get_value_to_display(target, YMF825_class.YMF825_PARM[target][parm]['name'])
                    Application_class.DISPLAY_LABELS[row][1].text = Application_class.DISPLAY_TEXTS[row][1]
                    
                    # Retain the label for the parameter to know where the parameter is on the display.
                    Application_class.LABEL_TO_DISPLAY[(target, YMF825_class.YMF825_PARM[target][parm]['name'], 0)] = (row, 1)
 
                    # Next parameter in the range
                    parm = parm + 1

                # Blank line
                else:
                    self.show_algorithm_chart(row)                        

        # OPERATORS parameter's page
        elif target == 'OPERATORS':
            # Show each display line
            for row in list(range(1,11)):
                # Show parameter
                if parm <= parm_last:
                    # Parameter name
                    Application_class.DISPLAY_TEXTS[row][0] = YMF825_class.YMF825_PARM[target][parm]['name'] + ':'
                    Application_class.DISPLAY_LABELS[row][0].text = Application_class.DISPLAY_TEXTS[row][0]

                    # Parameter values for each operator
                    for col in list(range(1,5)):
                        Application_class.DISPLAY_TEXTS[row][col] = YMF825_obj.get_value_to_display(target, YMF825_class.YMF825_PARM[target][parm]['name'], col - 1)
                        Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]
                    
                        # Retain the label for the parameter to know where the parameter is on the display.
                        Application_class.LABEL_TO_DISPLAY[(target, YMF825_class.YMF825_PARM[target][parm]['name'], col - 1)] = (row, col)
 
                        # WAVE has a special treatment
                        if YMF825_class.YMF825_PARM[target][parm]['name'] == 'WAVE':
                            # Show the wave names
                            show_wave_names = True                            
 
                    # Next parameter in the range
                    parm = parm + 1

                # Blank line (if needed)
                else:
                    for col in list(range(5)):
                        Application_class.DISPLAY_TEXTS[row][col] = ''
                        Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]

                    # Show wave names
                    if row >= 6 and row <= 9:
                        if show_wave_names:
                            Application_class.DISPLAY_TEXTS[row][0] = 'wav' + str(row - 5) + ':'
                            Application_class.DISPLAY_LABELS[row][0].text = Application_class.DISPLAY_TEXTS[row][0]
                            Application_class.DISPLAY_TEXTS[row][1] = YMF825_obj.get_value_to_display('OPERATORS', 'WAVE', row - 6, True)
                            Application_class.DISPLAY_LABELS[row][1].text = Application_class.DISPLAY_TEXTS[row][1]

                    # Alogorithm line on the bottom
                    elif row == 10:
                        Application_class.DISPLAY_TEXTS[row][0] = 'ALGO:'
                        Application_class.DISPLAY_LABELS[row][0].text = Application_class.DISPLAY_TEXTS[row][0]
                        Application_class.DISPLAY_TEXTS[row][1] = YMF825_obj.get_value_to_display('GENERAL', 'ALGO')
                        Application_class.DISPLAY_LABELS[row][1].text = Application_class.DISPLAY_TEXTS[row][1]

        # EQUALIZERS parameter's page
        elif target == 'EQUALIZERS':
            # Show each display line
            for row in list(range(1,11)):
                # Show parameter
                if parm <= parm_last:
                    # No data space
                    for col in list(range(2,5)):
                        Application_class.DISPLAY_TEXTS[row][col] = ''
                        Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]

                    # Parameter name
                    Application_class.DISPLAY_TEXTS[row][0] = YMF825_class.YMF825_PARM[target][parm]['name'] + ':'
                    Application_class.DISPLAY_LABELS[row][0].text = Application_class.DISPLAY_TEXTS[row][0]
 
                    # Parameter value
                    Application_class.DISPLAY_TEXTS[row][1] = YMF825_obj.get_value_to_display(target, YMF825_class.YMF825_PARM[target][parm]['name'], unit)
                    Application_class.DISPLAY_LABELS[row][1].text = Application_class.DISPLAY_TEXTS[row][1]
                    
                    # Retain the label for the parameter to know where the parameter is on the display.
                    Application_class.LABEL_TO_DISPLAY[(target, YMF825_class.YMF825_PARM[target][parm]['name'], unit)] = (row, 1)
 
                    # Next parameter in the range
                    parm = parm + 1

                # Blank line
                else:
                    for col in list(range(5)):
                        Application_class.DISPLAY_TEXTS[row][col] = ''
                        Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]

        # SAVE/LOAD parameter's page
        elif target == 'SAVE' or target == 'LOAD':
            if target == 'LOAD':
                YMF825_obj.find_sound_files()
            
            # Show each display line
            for row in list(range(1,11)):
                # Show parameter
                if parm <= parm_last:
                    # No data space
                    for col in list(range(2,5)):
                        Application_class.DISPLAY_TEXTS[row][col] = ''
                        Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]

                    # Parameter name
                    Application_class.DISPLAY_TEXTS[row][0] = YMF825_class.YMF825_PARM[target][parm]['name'] + ':'
                    Application_class.DISPLAY_LABELS[row][0].text = Application_class.DISPLAY_TEXTS[row][0]
 
                    # Parameter value
                    Application_class.DISPLAY_TEXTS[row][1] = YMF825_obj.get_value_to_display(target, YMF825_class.YMF825_PARM[target][parm]['name'])
                    Application_class.DISPLAY_LABELS[row][1].text = Application_class.DISPLAY_TEXTS[row][1]
                    
                    # Retain the label for the parameter to know where the parameter is on the display.
                    Application_class.LABEL_TO_DISPLAY[(target, YMF825_class.YMF825_PARM[target][parm]['name'], 0)] = (row, 1)
 
                    # Next parameter in the range
                    parm = parm + 1

                # Blank line
                else:
                    for col in list(range(5)):
                        Application_class.DISPLAY_TEXTS[row][col] = ''
                        Application_class.DISPLAY_LABELS[row][col].text = Application_class.DISPLAY_TEXTS[row][col]

    # Treat 8encoder events
    def task_8encoder(self):
#        print('8Encoder:', M5Stack_8Encoder_class.status)
        # Change the editor page
        if M5Stack_8Encoder_class.status['on_change']['rotary_inc'][7]:
            inc = 1 if M5Stack_8Encoder_class.status['rotary_inc'][7] <= 127 else -1
            Application_class.DISPLAY_PAGE = (Application_class.DISPLAY_PAGE + inc) % Application_class.DISPLAY_PAGE_MAX
            self.change_page()
            return

        # Page format
        disp_frmt = Application_class.DISPLAY_PAGE_FORMAT[Application_class.DISPLAY_PAGE]
        
        # Parameters target and its range
        target = disp_frmt['target']
        parm = disp_frmt['range'][0]
        parm_last = disp_frmt['range'][1]
        parm_unit = disp_frmt['unit']

        # Editor control
        algorithm_edited = False
        operator_edited  = False
        equalizer_edited = False
        for rotary in list(range(7)):
            if M5Stack_8Encoder_class.status['on_change']['rotary_inc'][rotary]:
                inc = 1 if M5Stack_8Encoder_class.status['rotary_inc'][rotary] <= 127 else -1
                
                # Items to be edited
                if parm <= parm_last:
                    # Rotation event on the rotary encoder
                    parm_name = YMF825_class.YMF825_PARM[target][parm]['name']
                    YMF825_obj.increment_parameter_value(inc, target, parm_name, parm_unit)
                    self.show_parameter(target, parm_name, parm_unit)
                    
                    if target == 'GENERAL' or target == 'OPERATORS':
                        operator_edited = True
                        if parm_name == 'ALGO':
                            algorithm_edited = True

                    if target == 'EQUALIZERS' and (parm_name == 'FREQ' or parm_name == 'Qfct'):
                        equalizer_edited = True

                    # Load bank was changed
                    if target == 'LOAD' and parm_name == 'BANK':
                        YMF825_obj.find_sound_files()
                        self.show_parameter(target, 'NUM.', 0)

                else:
                    break
                        
            # Next parameter
            parm = parm + 1

        if target == 'GENERAL' or target == 'OPERATORS':
            if operator_edited:
                YMF825_obj.send_edited_sound_param()
            
            if algorithm_edited:
                for row in list(range(4,11)):
                    self.show_algorithm_chart(row)

        elif target == 'EQUALIZERS':
            if equalizer_edited:
                YMF825_obj.send_equalizer_parameters(parm_unit)
            
        elif target == 'SAVE':
            parm = YMF825_obj.get_value(target, 'SAVE')
            if parm is not None:
                if parm['value'] == 2:
                    YMF825_obj.save_parameter_file()
                    parm['value'] = 0
                    sleep(1.0)
                    self.show_parameter(target, 'SAVE', 0)
            
        elif target == 'LOAD':
            parm = YMF825_obj.get_value(target, 'LOAD')
            if parm is not None:
                # Load a file
                if parm['value'] == 2:
                    result = YMF825_obj.load_parameter_file()
                    parm['value'] = 0
                    if result:
                        YMF825_obj.send_edited_sound_param()
                        for eqno in list(range(3)):
                            YMF825_obj.send_equalizer_parameters(eqno)

                    sleep(1.0)
                    self.show_parameter(target, 'LOAD', 0)
                
                # Search files
                elif parm['value'] == 4:
                    YMF825_obj.find_sound_files()
                    sleep(1.0)
                    parm['value'] = 0
                    self.show_parameter(target, 'LOAD', 0)
                    self.show_parameter(target, 'NUM.', 0)


#########################
######### MAIN ##########
#########################
if __name__=='__main__':
#    microcontroller.cpu.frequency = 250_000_000  # run at 250 MHz instead of 125 MHz

    # Create an Application and an OLED object
    Application = Application_class()
    OLED_obj = OLED_SH1107_128x128_class()
    
    # Create an Encode and a MIDI object
    Encoder_obj = M5Stack_8Encoder_class()
    MIDI_obj = MIDI_class()

    # Start the application with showing the editor top page.
    Application.start()
    
    # Seach a USB MIDI device to connect
    MIDI_obj.look_for_usb_midi_device()
    
    # Create a YMF825 synthesizer object
    YMF825_obj = YMF825_class()

    # YMF825 Test Sounds
    print("Opening melody")
    opening_melody = [(67,0.2),(69,0.2),(71,0.2),(72,1.0)]
    for note in opening_melody:
        YMF825_obj.note_on(note[0], 24)
        sleep(note[1])
        YMF825_obj.note_on(note[0],  0)

    # Show the parameter editor top page.
    print("START async TASKS.")
    Application.change_page()

    #####################################################
    # Start application
    asyncio.run(main())
    #####################################################
    # END
    #####################################################


