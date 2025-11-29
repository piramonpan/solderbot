""" This Python script calls the GCodeWriter class and is used to control the 
GRBL """

# imports
import serial
import time
import json
from serial.tools import list_ports
from gcodewriter import GCodeWriter as writer

# constants
PORT = "COM7" # change to correct port
BAUDRATE = 115200
HEIGHT = 20 # (in mm)
LINE_FEEDRATE = 50 # TO DO: figure out the best feedrate for soldering lines
SCALE = 2.5 # distance between holes (in mm) <-- i think? need to double check

###############################################################################
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

def load_json():
    """ Loads the json file sent from the GUI 
    parameters: None
    returns: 
        data: the data within the json file 
    """
    data = {}

    try:
        with open('board_data.json', 'r') as file:
            data = json.load(file)
    
    except FileNotFoundError:
        print("Error: The file was not found.")
    
    return data

def format_json(json_data) -> list:
    """ Reads and formats data from json file into a list
    parameters:
        json_data: data loaded in from the json file
    returns:
        solder_list: formated list of points/lines that the user wants to 
                    solder
    """
    solder_list = []

    points = json_data["points"]
    lines = json_data["lines"]

    for point in points:
        solder_list.append(("point", point))

    for line in lines:
        start = line["start"]
        end = line["end"]
        solder_list.append(("line", start, end))

    # TO DO: get corner coordinates

    ## uncomment for debugging
    #for solder in solder_list:
    #    print(f"{solder}")

    return solder_list

def generate_gcode(data_list: list, last_col) -> list:
    """ Generates a list of GCODE commands based on the points/lines in the 
    json file. This function conducts the 'path planning' 
    parameters:
        data_list: list of points and lines from the json file
        last_col: last column on the protoboard
    returns:
        commands: list of GCODE commands
    """
    commands = []

    # reset and go to reference point
    commands.append(writer.reset())

    for col in range(0, last_col):
        for data in data_list:
            x, y = data[1]

            if x == col and data[0] == "point":
                # move to point
                x_coord = x * SCALE
                y_coord = y * SCALE
                commands.append(writer.rapid_positioning(x_coord, y_coord))

                # lower end effector and solder
                commands.append(writer.move_up_down(-HEIGHT))     # TO DO: figure out vertical distance required
                commands.append(writer.wait(5000))

                # raise end effector once soldering is complete
                commands.append(writer.move_up_down(HEIGHT))
            elif x == col and data[0] == "line":
                # move to point and lower end effector
                x_coord = x * SCALE
                y_coord = y * SCALE
                commands.append(writer.rapid_positioning(x_coord, y_coord))
                commands.append(writer.move_up_down(-HEIGHT))

                # slowly drag solder to create line
                end_x, end_y = data[2]
                x_coord = end_x * SCALE
                y_coord = end_y * SCALE
                commands.append(writer.linear_interpolation(x_coord, y_coord, 
                                                            LINE_FEEDRATE))
                commands.append(writer.move_up_down(HEIGHT))
    
    return commands

def send_commands(serial_port, commands):
    """ Sends GCODE command to gantry microcontroller by writing to serial 
    port.
    parameters:
        serial_port: the COM port connecting the laptop to the gantry's 
                    microcontroller
        commands: list of GCODE commands to send to microcontroller
    returns: None
    """
    # point to serial port and clear any startup messages from the buffer
    ser = serial.Serial(port=serial_port, baudrate=BAUDRATE)
    time.sleep(2)
    ser.flushInput()

    # send gcode commands
    for command in commands:
        ser.write((command + '\n').encode())

    print("Soldering complete")
    
def set_reference():

    # move to initial hard coded reference point
    ## GUI asks user if this position is correct
    # if position is correct:
        # command.append(writer.set_reference())
        # send_commands
    # else:
        ## user moves gantry to correct reference point
        # command.append(writer.set_reference())
        # send_commands
    return

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

    z = writer.move_up_down(5)
    ser.write((z + '\n').encode())

def main():
    # test port connection
    '''connection = check_ports(PORT.device)

    if connection is True:
        # run test code
        gcode_test("COM7")
    else: 
        print(f"Unable to connect to gantry through {PORT}")'''
    
    # read json file
    data = load_json()
    format_json(data)


if __name__ == '__main__':
    main()