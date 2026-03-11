#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger for Victor multimeters with USB/RS232. It's been verified with Victor 70C, but likely works with others with 4-digit display.
Reference: "DMM Communication Protocol"
"""

"""
TODO Graphical UI
TODO Choose communication port via enumerated list
TODO Choose file to store log to
TODO Handle starting and stopping logging
"""

import csv
import datetime
import glob
import math
import serial
import sys
import traceback

__author__ = "Anders Borg"
__copyright__ = "Copyright 2021, Abiro AB"
__credits__ = ["Anders Borg"]
__license__ = "Apache"
__version__ = "0.1"
__maintainer__ = "Anders Borg"
__email__ = "anders.borg@abiro.com"
__status__ = "Prototype"

# Enumerate all serial ports
def serial_ports():
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

print("Logger for Victor multimeters with USB/RS232.")

ports = serial_ports()

# User configuration
ConfigPort = input("Port (" + ", ".join(ports) + "): ")
ConfigFile = input("File (VictorLogger.csv): ")
ConfigMode = input("Mode (normal, all, timevalues, values): ")

if ConfigPort == '':
    ConfigPort = ports[0]
    
if ConfigFile == '':
    ConfigFile = 'VictorLogger.csv'
    
if ConfigMode == 'all':
    UseCounter = True
    UseTime = True
    UseScale = True
    UseUnit = True
    UseBar = True
    UseMode = True
    UseRedundant = True
elif ConfigMode == 'timevalues':
    UseCounter = False
    UseTime = True
    UseScale = True
    UseUnit = False
    UseBar = False
    UseMode = False
    UseRedundant = False
elif ConfigMode == 'values':
    UseCounter = False
    UseTime = False
    UseScale = True
    UseUnit = False
    UseBar = False
    UseMode = False
    UseRedundant = False
else: # normal
    UseCounter = True
    UseTime = True
    UseScale = True
    UseUnit = True
    UseBar = False
    UseMode = True
    UseRedundant = False
    
print("Reading from: " + ConfigPort)
print("Writing to: " + ConfigFile)
print("Break and save with Ctrl+C")

ser = serial.Serial(ConfigPort, 2400)

csvfile = open(ConfigFile, 'w', newline='')
filewriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

# Header row
output = []
if UseCounter:
    output.append("Sample")
if UseTime:
    output.append("Time")
output.append("Value")
if UseUnit:
    output.append("Unit")
if UseBar:
    output.append("Bar")
if UseMode:
    output.append("Mode")

print(" ".join(output))
filewriter.writerow(output)

counter = 0

while True:
    try:
        output = []

        line = ser.readline()
        #print("Debug: " + " ".join(format(x, '02x') for x in line))

        if len(line) >= 12:
            # Extract individual values as per specification
            X1 = chr(line[0]) # Sign
            X2 = chr(line[1]) # Digit 1
            X3 = chr(line[2]) # Digit 2
            X4 = chr(line[3]) # Digit 3
            X5 = chr(line[4]) # Digit 4
            X6 = chr(line[5]) # Space
            X7 = chr(line[6]) # Decimal point
            X8 = line[7] # Flags
            X9 = line[8] # Flags
            X10 = line[9] # Flags
            X11 = line[10] # Flags
            X12 = line[11] # Bar

            # Determine the unit, scale and mode
            unit = ""
            scale = 1
            scaleName = ""
            mode = []

            if X8 & 0b00000001 and UseRedundant:
                mode.append("RS232")
            if X8 & 0b00000010:
                mode.append("Hold")
            if X8 & 0b00000100:
                mode.append("Relative")
            if X8 & 0b00001000:
                mode.append("AC")
            if X8 & 0b00010000:
                mode.append("DC")
            if X8 & 0b00100000:
                mode.append("Automatic")

            if X9 & 0b00000010:
                scaleName = "nano"
                scale = 1E-9
            if X9 & 0b00000100 and UseRedundant:
                mode.append("Battery")
            if X9 & 0b00001000 and UseRedundant:
                mode.append("Autooff")
            if X9 & 0b00010000:
                mode.append("Minimum")
            if X9 & 0b00100000:
                mode.append("Maximum")

            if X10 & 0b00000010:
                unit = "%"
            if X10 & 0b00000100:
                mode.append("Diode")
            if X10 & 0b00001000:
                mode.append("Beep")
            if X10 & 0b00010000:
                scaleName = "mega"
                scale = 1E6
            if X10 & 0b00100000:
                scaleName = "kilo"
                scale = 1E3
            if X10 & 0b01000000:
                scaleName = "milli"
                scale = 1E-3
            if X10 & 0b10000000:
                scaleName = "micro"
                scale = 1E-6

            if X11 & 0b00000001:
                unit = "Fahrenhet"
            if X11 & 0b00000010:
                unit = "Celsius"
            if X11 & 0b00000100:
                unit = "Farad"
            if X11 & 0b00001000:
                unit = "Hertz"
            if X11 & 0b00010000:
                unit = "Amplification"
            if X11 & 0b00100000:
                unit = "Ohm"
            if X11 & 0b01000000:
                unit = "Ampere"
            if X11 & 0b10000000:
                unit = "Volt"

            # Determine the value
            if X2 != "?":
                if X7 == "0":
                    value = float(X2 + X3 + X4 + X5)
                elif X7 == "1":
                    value = float(X2 + "." + X3 + X4 + X5)
                elif X7 == "2":
                    value = float(X2 + X3 + "." + X4 + X5)
                elif X7 == "4":
                    value = float(X2 + X3 + X4 + "." + X5)
                else:
                    value = float('nan')
            else:
                value = float('nan')

            if not math.isnan(value):
                if X1 == "-":
                    value = -value

                if UseScale:
                    value *= scale

            # Present the results

            # Present the counter
            if UseCounter:
                counter += 1
                output.append(str(counter))

            # Present the time
            if UseTime:
                time = datetime.datetime.now()
                output.append(str(time.strftime('%Y-%m-%d %H:%M:%S')))

            # Present the value
            output.append(str("%.8g" % value))

            if UseUnit:
                if not UseScale and scaleName != "":
                    unit = scaleName + " " + unit

                output.append(str(unit))

            # Present the bar
            if UseBar:
                bar = X12
                if bar >= 128:
                    bar -= 256

                output.append(str(bar))

            # Present the mode
            if UseMode:
                output.append(str(" ".join(mode)))

            # Output the result
            print("\t".join(output))
            filewriter.writerow(output)

    except KeyboardInterrupt:
        print("Alrighty then!")
        break
    except ClearCommError:
        print("Lost the USB connection!")
        break
    except:
        traceback.print_exc()
        break

csvfile.close()
ser.close()

print("Logging stopped and log saved!")