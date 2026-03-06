import serial
import RPi.GPIO as GPIO
import time
import os
from serial.tools import list_ports

# Waveshare SX1262 868M LoRa HAT
# M0 = BCM22 (Physical pin 15), M1 = BCM27 (Physical pin 13)
# Modes via M0/M1:
#   Normal (TX/RX):  M0=LOW(0),  M1=LOW(0)
#   Configuration:   M0=LOW(0),  M1=HIGH(1)   ← register write
#   WOR:             M0=HIGH(1), M1=LOW(0)
#   Sleep:           M0=HIGH(1), M1=HIGH(1)

class LoRaHardware:
    def __init__(self, serial_port=None, baudrate=9600, m0_pin=None, m1_pin=None):
        serial_port = serial_port or os.environ.get('LORA_SERIAL_PORT', '/dev/ttyS0')
        m0_pin = m0_pin if m0_pin is not None else int(os.environ.get('LORA_M0_PIN', '22'))
        m1_pin = m1_pin if m1_pin is not None else int(os.environ.get('LORA_M1_PIN', '27'))
        try:
            self.ser = serial.Serial(serial_port, baudrate, timeout=1)
        except serial.SerialException:
            ports = [p.device for p in list_ports.comports()
                     if 'AMA' in p.device or 'USB' in p.device or 'S0' in p.device]
            if ports:
                self.ser = serial.Serial(ports[0], baudrate, timeout=1)
            else:
                raise RuntimeError(f"No LoRa serial port found. Tried {serial_port} and auto-detect.")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(m0_pin, GPIO.OUT)
        GPIO.setup(m1_pin, GPIO.OUT)
        self.m0_pin = m0_pin
        self.m1_pin = m1_pin
        self.set_mode(0, 0)  # Start in Normal mode

    def set_mode(self, m0, m1):
        GPIO.output(self.m0_pin, m0)
        GPIO.output(self.m1_pin, m1)
        time.sleep(0.1)

    def write(self, data: bytes):
        self.ser.write(data)

    def read(self) -> bytes:
        if self.ser.in_waiting:
            time.sleep(0.05)  # let the full packet arrive
            return self.ser.read(self.ser.in_waiting)
        return b''

    def flush(self):
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
