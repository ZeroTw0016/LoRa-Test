import serial
import RPi.GPIO as GPIO
import time
import os
from serial.tools import list_ports

class LoRaHardware:
    def __init__(self, serial_port=None, baudrate=9600, m0_pin=11, m1_pin=7):
        # Allow override by environment variable
        serial_port = serial_port or os.environ.get('LORA_SERIAL_PORT', '/dev/ttyAMA0')
        try:
            self.ser = serial.Serial(serial_port, baudrate, timeout=1)
        except serial.SerialException:
            # Try to auto-detect serial port
            ports = [p.device for p in list_ports.comports() if 'AMA' in p.device or 'USB' in p.device or 'S0' in p.device]
            if ports:
                self.ser = serial.Serial(ports[0], baudrate, timeout=1)
            else:
                raise RuntimeError(f"No LoRa serial port found. Tried {serial_port} and auto-detect.")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(m0_pin, GPIO.OUT)
        GPIO.setup(m1_pin, GPIO.OUT)
        self.m0_pin = m0_pin
        self.m1_pin = m1_pin

    def set_mode(self, m0, m1):
        GPIO.output(self.m0_pin, m0)
        GPIO.output(self.m1_pin, m1)
        time.sleep(0.1)

    def write(self, data):
        self.ser.write(data)

    def read(self):
        if self.ser.in_waiting:
            return self.ser.read(self.ser.in_waiting)
        return b''
