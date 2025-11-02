import time
from .gcode_processor import GcodeProcessor
import serial


class GRBLController(GcodeProcessor):
    def __init__(self, config, serial_port: str, baudrate=115200):
        GcodeProcessor.__init__(self)
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.parameters = config["parameters"]
        self.gcode = None
        self.feedrate = None
        self.homed = False
        self.relative = False
        self.initialized = False
        # TODO: implement position tracking
        self.x = None
        self.y = None
        self.z = None

        try:
            self.ser = serial.Serial(serial_port, baudrate=baudrate, timeout=1)
        except (IOError, serial.SerialException):
            print(f'GRBL: FAILED to establish serial connection through port {serial_port}')
            raise
        finally:
            try:
                self.ser.close()
            except AttributeError as e:
                print(f'GRBL: FAILED to connect - make sure serial device is plugged in')
                raise e
            try:
                self.ser = serial.Serial(serial_port, baudrate=baudrate, timeout=1)
            except (IOError, serial.SerialException):
                print(f'GRBL: FAILED to extablish connection through port {serial_port}')
                raise

            time.sleep(2)

            print('GRBL: Connection established - SUCCESS')

            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

        try:
            self._initialize()
        except Exception:
            print('GRBL: Unable to initialize')
        finally:
            self.initialized = True
            print('GRBL: Initialized')

    # def __del__(self):
    #     if self.gcode is not None:
    #         self.gcode.close()
    #     self.ser.close()

    def reconnect(self, time_out=3 * 60):
        """
        Attempts to reconnect to arduino within a period of time given
        :param time_out: the length of time it tries to reconnect for
        """
        reconnected = False
        self.ser.close()

        for i in range(0, time_out):

            time.sleep(1)

            try:
                self.ser = serial.Serial(self.serial_port, baudrate=self.baudrate, timeout=1)
            except Exception:
                self.ser.close()
                pass

            if self.ser.is_open:
                reconnected = True
                break

        if not reconnected:
            print(f'GRBL: Failed to reconnect...')

    def write(self, data, attempts=10):
        """
        :param data: The GRBL command to be sent.
        :param attempts: Number of attempts to write to GRBL
        :return: The sent command.
        """
        len_data = None
        while len_data is None:
            try:
                attempts -= 1
                finalstring = data + '\n'
                self.ser.reset_input_buffer()
                len_data = self.ser.write(finalstring.encode())
                time.sleep(0.2)
            except (serial.SerialTimeoutException, serial.SerialException) as e:
                print(f"failed to send {data} to GRBL to {e}. Attempts remaining: {attempts}")

        return len_data

    def read(self):
        """
        :return: GRBL response.
        """
        line = self.ser.readline()

        try:
            line = line.decode()
        except UnicodeDecodeError('GRBL: Failed to decode...ignoring current string') as e:
            raise e

        line = line.rstrip()

        return line

    def _set_grbl_parameters(self):
        """
        :return: Boolean representing the state of the parameter setting.
        """
        try:
            self.ser.flushInput()

            for parameter, value in self.parameters.items():
                gcode = f"{parameter}={value}\n"
                self.ser.write(gcode.encode())
                time.sleep(0.1)
                self.read()

            return True
        except Exception as e:
            print(f"Error setting GRBL parameters: {e}")
            return False

    def _initialize(self):
        """
        Initializes GRBL.
        """
        response = self._set_grbl_parameters()
        if response:
            self.write("\r\n\r\n")
            time.sleep(2)
            self.ser.flushInput()
        else:
            print("Unable to initialize GRBL")

    def stream_gcode(self, file_path):
        """
        :param file_path: Gcode file to stream.
        """
        self.gcode = open(file_path, 'r')

        for line in self.gcode:
            l = line.strip()
            print('Sending: ' + l, )
            self.write(l + '\n')
            grbl_out = self.read()
            print(' : ' + str(grbl_out))

    def home(self):
        """
        Executes the GRBL homing cycle.
        """
        self.write("$H\n")
        if 'ok' == self.read():
            self.homed = True

    def kill_lock(self):
        """
        Overrides the alarm lock to allow for axis movement.
        """
        self.write("$X\n")
        grbl_out = self.read()
        print(' : ' + str(grbl_out))

    def status(self):
        """
        :return: Active GRBL state and current machine positions.
        """
        self.write("?\n")
        time.sleep(0.1)
        response = self.read()

        status = {}
        for item in response.split("|"):
            parts = item.split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                status[key] = value

        return status

    # TODO: finalize
    def move(self, x=None, y=None, z=None, i=None, j=None, k=None, clockwise=False, velocity=None, relative=False,
             circular=False, wait=True):

        if velocity is not None and velocity is not self.feedrate:
            feedrate_command = self.velocity_to_feedrate(velocity)
            self.ser.write(feedrate_command)
            self.feedrate = velocity
            time.sleep(1)

        if self.relative != relative:
            mode = self.positioning(relative)
            self.ser.write(mode)
            self.relative = relative
            time.sleep(1)

        if circular:
            command = self.circular_interpolation_gcode(x, y, z, i, j, k, clockwise)
        else:
            command = self.linear_interpolation_gcode(x, y, z)

        if wait:
            self.write(command)
            # self.wait_until()
        else:
            self.write(command)

    # TODO: this function is not working, GRBL returns OK and command receipt
    def wait_until(self, timeout=30, period=0.5):
        """
        :param timeout: Time in seconds for waiting
        :param period: Polling period in seconds
        :return: Boolean value representing if the requirement was met
        """
        mustend = time.time() + timeout
        while time.time() < mustend:
            if self.read() == "ok":
                print("Read ok")
                return True
            time.sleep(period)
            print("Waiting")
        return False

    def disconnect(self):
        self.ser.close()
