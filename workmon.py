#!/usr/bin/env python3
"""
Monitor table position and display on/off state.
"""

import time
import serial

import adafruit_us100


# distance sensor
uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=1)
us100 = adafruit_us100.US100(uart)

# Current sensor
ser = serial.Serial('/dev/ttyAMA0', 38400)


def sensor_loop():
    """
    Acquire data from the sensors.
    """
    while True:
        # Read one line from the serial buffer
        line = ser.readline().decode('ascii')

        # Remove the trailing carriage return line feed
        line = line[:-2]

        # Create an array of the data
        Z = line.split(' ')

        # Print it nicely
        if len(Z) > 15:
            print("----------")
            print("          \tCT1\tCT2\tCT3")
            print("RealPower:\t%s\t%s\t%s" % (Z[1], Z[6], Z[11]))
            print("AppaPower:\t%s\t%s\t%s" % (Z[2], Z[7], Z[12]))
            print("Irms     :\t%s\t%s\t%s" % (Z[3], Z[8], Z[13]))
            print("Vrms     :\t%s\t%s\t%s" % (Z[4], Z[9], Z[14]))
            print("PowerFact:\t%s\t%s\t%s" % (Z[5], Z[10], Z[15]))

        print("Temperature: ", us100.temperature)
        time.sleep(0.5)
        print("Distance: ", us100.distance)
        time.sleep(0.5)

        time.sleep(3)


def main():
    """
    Main prog
    """
    try:
        sensor_loop()
    except KeyboardInterrupt:
        ser.close()


if __name__ == "__main__":
    main()
