import serial
import RPi.GPIO as GPIO
import time

class LoRaHardware:
    def __init__(self, serial_port='/dev/ttyAMA0', baudrate=9600, m0_pin=11, m1_pin=7):
        self.ser = serial.Serial(serial_port, baudrate, timeout=1)
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
