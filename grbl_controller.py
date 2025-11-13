""" This Python script calls the GCodeWriter class and is used to control the 
GRBL """

# imports
import serial
import time
from serial.tools import list_ports
from gcodewriter import GCodeWriter as writer

# constants
PORT = "COM7" # change to correct port
BAUDRATE = 115200

def list_available_ports():
    """ Lists available ports on laptop """

    ports = list_ports.comports()
    if not ports:
        print("No serial ports found.")
    else:
        print("Available serial ports:")
        for port in ports:
            print(f"  {port.device}")

def check_ports(port):
    """ Tests port connection by attempting to open input port 
    parameters:
        port: input port to test
    returns:
        True if port was successfully opened
        False otherwise
    """

    try:
        # Attempt to open the port with a short timeout
        ser = serial.Serial(port=port, baudrate=BAUDRATE, timeout=0.5) 
        ser.close() # Close immediately if successful
        return True
    except serial.SerialException:
        print()
        return False

def gcode_test(serial_port):
    """ Test basic movement of gantry 
    parameters: 
        serial_port: the COM port connecting the laptop to the gantry's 
                        microcontroller
    returns: None
    """
    ser = serial.Serial(port=serial_port, baudrate=BAUDRATE)
    time.sleep(2)
    ser.flushInput() # Clear any startup messages from the buffer

    # reset and go to reference point
    reset = writer.reset()
    ser.write((reset + '\n').encode())

    # set positioning to absolute
    positioning = writer.positioning("absolute")
    ser.write((positioning + '\n').encode())

    y = writer.rapid_positioning(x=None, y=50)
    ser.write((y + '\n').encode())

    x = writer.rapid_positioning(x=20, y=50)
    ser.write((x + '\n').encode())

    y = writer.rapid_positioning(x=20, y=None)
    ser.write((y + '\n').encode())

    x = writer.rapid_positioning(x=40, y=None)
    ser.write((x + '\n').encode())

    y = writer.rapid_positioning(x=40, y=25)
    ser.write((y + '\n').encode())

    z = writer.move_up_down(5) # TO DO: figure if positive or negative z is down
    ser.write((z + '\n').encode())

def main():
    # test port connection
    connection = check_ports(PORT.device)

    if connection is True:
        # run test code
        gcode_test("COM7")
    else: 
        print(f"Unable to connect to gantry through {PORT}")


if __name__ == '__main__':
    main()