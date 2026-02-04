"""This Python script calls the GCodeWriter class and is used to control the
GRBL"""

# imports
import serial
import time
import json
from serial.tools import list_ports
from core.gcodewriter import GCodeWriter as writer

# constants
PORT = "COM10"  # change to correct port
BAUDRATE = 115200
HEIGHT = 1  # (in mm)
LINE_FEEDRATE = 50  # TO DO: figure out the best feedrate for soldering lines
SCALE = 2.5  # distance between holes (in mm) <-- i think? need to double check
SOLDER_TIME = 5000  # how long the solder is held over a point (in ms)
SOLDER_DISPENSE_RATE = 160  # spool feed motor speed (in rpm, lowest speed: 160)

############################## Helper Functions ###############################


class GRBLController:
    """Class to handle GRBL communication and GCODE generation"""

    def __init__(
        self,
        port: str,
        baudrate: int = BAUDRATE,
        timeout: float = 1.0,
        height: float = HEIGHT,
        line_feedrate: float = LINE_FEEDRATE,
        scale: float = SCALE,
        solder_time: int = SOLDER_TIME,
        solder_dispense_rate: int = SOLDER_DISPENSE_RATE,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.height = height
        self.line_feedrate = line_feedrate
        self.scale = scale
        self.solder_time = solder_time
        self.solder_dispense_rate = solder_dispense_rate

        ## SERIAL CONNECTION and write ##
        self.writer = writer()
        self.ser: serial.Serial = None  # type: ignore

    def list_available_ports(self):
        """Lists available ports on laptop"""

        ports = list_ports.comports()
        if not ports:
            print("No serial ports found.")
        else:
            print("Available serial ports:")
            for port in ports:
                print(f"  {port.device}")

    def connect(self, port: str):
        try:
            self.ser = serial.Serial(port=port, baudrate=BAUDRATE)
            print(f"Successfully connected to port {port}")
            return True
        
        except serial.SerialException:
            print(f"Failed to connect to port {port}")
            self.list_available_ports()
            return False
        
    def poll_grbl(self):
        """Polls GRBL until it reports Idle."""
        while True:
            self.ser.write(b"?")  # status report
            time.sleep(0.1)

            if self.ser.in_waiting:
                status = self.ser.readline().decode().strip()
                print("STATUS:", status)

                if "Idle" in status:
                    return
            time.sleep(0.2)

    def gcode_test(self):
        """Test basic movement of gantry
        parameters:
            serial_port: the COM port connecting the laptop to the gantry's
                            microcontroller
        returns: None
        """
        time.sleep(2)
        self.ser.flushInput()  # Clear any startup messages from the buffer

        # unlock GRBL
        self.ser.write(b"$X\n")
        time.sleep(0.1)
        while self.ser.in_waiting:
            print("Unlock:", self.ser.readline().decode().strip())

        # reset and go to reference point
        """reset = writer.reset()
        ser.write((reset + '\n').encode())"""

        # set positioning to absolute
        positioning = self.writer.positioning("absolute")
        self.ser.write((positioning + "\n").encode())

        dispense = self.writer.start_dispensing(self.solder_dispense_rate)
        self.ser.write((dispense + "\n").encode())

        time.sleep(3)

        stop = self.writer.stop_dispensing()
        self.ser.write((stop + "\n").encode())

        retract = self.writer.retract_solder(self.solder_dispense_rate)
        self.ser.write((retract + "\n").encode())

        time.sleep(3)

        stop = self.writer.stop_dispensing()
        self.ser.write((stop + "\n").encode())

        """x = self.writer.rapid_positioning(x=40, y=None)
        self.ser.write((x + '\n').encode())

        y = self.writer.rapid_positioning(x=40, y=25)
        self.ser.write((y + '\n').encode())

        z = self.writer.move_up_down(5)
        self.ser.write((z + '\n').encode())"""

    ########################### Path Planning Functions ###########################

    def load_json(self) -> dict:
        """Loads the json file sent from the GUI
        parameters: None
        returns:
            data: the data within the json file
        """
        data = {}

        try:
            with open("board_data.json", "r") as file:
                data = json.load(file)

        except FileNotFoundError:
            print("Error: The file was not found.")

        return data

    def format_json(self, json_data: dict) -> list:
        """Reads and formats data from json file into a list
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
        # use corner coordinates to determine last column

        return solder_list

    def generate_gcode(self, data_list: list, last_col) -> list:
        """Generates a list of GCODE commands based on the points/lines in the
        json file. This function conducts the 'path planning'
        parameters:
            data_list: list of points and lines from the json file
            last_col: last column on the protoboard
        returns:
            commands: list of GCODE commands
        """
        commands = []

        # reset and go to reference point
        commands.append(self.writer.positioning("absolute"))
        commands.append(self.writer.reset())

        for col in range(0, last_col):
            for data in data_list:
                x, y = data[1]

                if x == col and data[0] == "point":
                    # move to point
                    x_coord = x * self.scale
                    y_coord = y * self.scale
                    commands.append(self.writer.rapid_positioning(x_coord, y_coord))

                    # lower end effector and solder
                    commands.append(
                        self.writer.move_up_down(-self.height)
                    )  # TO DO: figure out vertical distance required
                    commands.append(self.writer.start_dispensing(self.solder_dispense_rate))
                    commands.append(self.writer.wait(self.solder_time))
                    commands.append(self.writer.stop_dispensing())
                    # commands.append(writer.retract_solder(SOLDER_DISPENSE_RATE))

                    # raise end effector once soldering is complete
                    commands.append(self.writer.move_up_down(self.height))
                elif x == col and data[0] == "line":
                    # move to point and lower end effector
                    x_coord = x * self.scale
                    y_coord = y * self.scale
                    commands.append(self.writer.rapid_positioning(x_coord, y_coord))
                    commands.append(self.writer.move_up_down(-self.height))

                    # start dispensing solder
                    commands.append(self.writer.start_dispensing(self.solder_dispense_rate))

                    # slowly drag solder to create line
                    end_x, end_y = data[2]
                    x_coord = end_x * self.scale
                    y_coord = end_y * self.scale
                    commands.append(
                        self.writer.linear_interpolation(x_coord, y_coord, LINE_FEEDRATE)
                    )

                    # stop soldering
                    commands.append(self.writer.stop_dispensing())
                    # commands.append(writer.retract_solder(SOLDER_DISPENSE_RATE))
                    commands.append(self.writer.move_up_down(self.height))

        commands.append(self.writer.reset())

        return commands

    def send_commands(self, commands: list) -> None:
        """Sends GCODE command to gantry microcontroller by writing to serial
        port.
        parameters:
            serial_port: the COM port connecting the laptop to the gantry's
                        microcontroller
            commands: list of GCODE commands to send to microcontroller
        returns: None
        """
        # point to serial port and clear any startup messages from the buffer
        # time.sleep(2)

        # unlock GRBL
        self.ser.write(b"$X\n")
        time.sleep(0.1)
        while self.ser.in_waiting:
            print("Unlock:", self.ser.readline().decode().strip())

        # send gcode commands
        for command in commands:
            self.ser.write((command + "\n").encode())
            print(command)

            start = time.time()

            while True:
                if self.ser.in_waiting:
                    response = self.ser.readline().decode("utf-8").strip()
                    print(f"Received response: {response}")

                    # Check for the 'ok' response to know when it's safe to send the
                    # next command. Check is skipped is command was wait
                    if command == self.writer.wait(self.solder_time):
                        break
                    elif "ok" in response.lower():
                        break

                if time.time() - start > 10:
                    print("Timeout waiting for response")
                    break

            # get grbl status while sending commands
            self.poll_grbl()

            # wait after lowering end effector
            if command == self.writer.move_up_down(-self.height):
                print("waiting")
                time.sleep(self.solder_time / 1000)
            elif command == self.writer.start_dispensing(self.solder_dispense_rate):
                print("dispensing")
                time.sleep(3)

        print("Soldering complete")

    def start_soldering(self):
        """Main function to start the soldering process after loading json data """
        data = self.load_json()
        solder_list = self.format_json(data)
        commands = self.generate_gcode(solder_list, 24)  # TO DO: change 24 to last_col
        self.send_commands(commands)

    def emergency_stop(self):
        """Sends an emergency stop command to GRBL"""
        pass
        
    def set_reference(self):
        # move to initial hard coded reference point
        ## GUI asks user if this position is correct
        # if position is correct:
        # command.append(writer.set_reference())
        # else:
        ## user moves gantry to correct reference point
        # command.append(writer.set_reference())
        pass

if __name__ == "__main__":
    grbl = GRBLController(PORT)
    grbl.list_available_ports()
    connection = grbl.connect(PORT)

    if connection is True:
        print(f"Successfully connected to gantry through {PORT}")
        grbl.start_soldering()

    else:
        print(f"Unable to connect to gantry through {PORT}")
