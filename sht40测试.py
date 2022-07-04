import time
import struct
from machine import I2C
from micropython import const

SHT4X_DEFAULT_ADDR = const(0x44)  # SHT4X I2C Address
SHT4X_READSERIAL = const(0x89)  # Read Out of Serial Register
SHT4X_SOFTRESET = const(0x94)  # Soft Reset

i2c=I2C(0)
i2c.writeto(SHT4X_DEFAULT_ADDR, b'\x89')
time.sleep(0.1)
serial_number=i2c.readfrom(68,6)
#print(serial_number)
ser1 = serial_number [0:2]
ser1_crc = serial_number[2]
ser2 = serial_number[3:5]
ser2_crc = serial_number[5]
serial = (ser1[0] << 24) + (ser1[1] << 16) + (ser2[0] << 8) + ser2[1]
print(serial)
i2c.writeto(SHT4X_DEFAULT_ADDR, b'\x94')
time.sleep(0.001)
i2c.writeto(SHT4X_DEFAULT_ADDR, b'\xFD')
time.sleep(0.01)
measurements=i2c.readfrom(68,6)
#print(cs2)
temp_data = measurements[0:2]
temp_crc = measurements[2]
humidity_data = measurements[3:5]
humidity_crc = measurements[5]
temperature = struct.unpack_from(">H", temp_data)[0]
temperature = -45.0 + 175.0 * temperature / 65535.0
humidity = struct.unpack_from(">H", humidity_data)[0]
humidity = -6.0 + 125.0 * humidity / 65535.0
humidity = max(min(humidity, 100), 0)
print(temperature,humidity)

