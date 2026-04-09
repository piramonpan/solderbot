import serial
import time
import threading
import re

class ESP32:
    def __init__(self, bt_port="COM11"):
        self.bt_port = bt_port
        self.ser = None
        self._log_thread = None
        self._log_thread_stop = threading.Event()
        self._iron_on = False
        self.latest_temp_data = None  # (now, currentTemp, setpoint, pidOutput)

        def connect():
            try:
                print(f"Connecting to {self.bt_port}...")
                self.ser = serial.Serial(self.bt_port, 115200, timeout=2)
                time.sleep(2) # Give the connection a moment to settle
                print("Connection to ESP32 established.")
            except Exception as e:
                print(f"\nConnection Failed: {e}")
                print("Tip: Ensure the ESP32 is paired in your OS settings and the COM port is correct.")
                self.ser = None

        connect()
        self._start_log_thread()

    def send_message(self, message, timeout=5):
        """
        Sends a string to ESP32 and waits for an 'ACK' response.
        Returns the response string if successful, None otherwise.
        """
        if self.ser is None:
            print("ESP32 not connected — cannot send message.")
            return None
        try:
            print(f"Sending to ESP32: {message}")
            self.ser.reset_input_buffer()
            self.ser.write(f"{message}\n".encode('utf-8'))

            start_time = time.time()
            while (time.time() - start_time) < float(timeout):
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    if "ACK" in line:
                        return line
            return None  # Timed out
        except Exception as e:
            print(f"Communication error: {e}")
            return None
        
    def move_z_arm_down(self):
        response = self.send_message("MOVE_Z_DOWN")
        print(response)
        if response == "ACK: Z-Axis Down":
            print(f"ESP32 Response: {response}")
            return True
        else:
            print("Failed to receive ACK from ESP32 for MOVE_Z_DOWN command.")
            return False
    
    def move_z_arm_up(self):
        response = self.send_message("MOVE_Z_UP")
        if response == "ACK: Z-Axis Up":
            print(f"ESP32 Response: {response}")
            return True
        else:
            print("Failed to receive ACK from ESP32 for MOVE_Z_UP command.")
            return False
        
    def turn_on_soldering_iron(self):
        response = self.send_message("IRON_ON")
        if response == "ACK: IRON_ON":
            print(f"ESP32 Response: {response}")
            self._iron_on = True
            self._start_log_thread()
            return True
        else:
            print("Failed to receive ACK from ESP32 for IRON_ON command.")
            return False
        
    def turn_off_soldering_iron(self):
        self._stop_log_thread()
        response = self.send_message("IRON_OFF")
        if response == "ACK: IRON_OFF":
            print(f"ESP32 Response: {response}")
            self._iron_on = False
            self._start_log_thread()
            return True
        else:
            print("Failed to receive ACK from ESP32 for IRON_ON command.")
            self._start_log_thread()
            return False
        
    def set_temp(self, temperature: int):
        self._stop_log_thread()
        response = self.send_message(f"SET_TEMP_{temperature}")
        if response == f"ACK: SET_TEMP_{temperature}":
            print(f"ESP32 Response: {response}")
            self._start_log_thread()
            return True
        else:
            print("Failed to receive ACK from ESP32 for SET_TEMP command.")
            print(f"ESP32 Response: {response}")
            self._start_log_thread()
            return False

    def close(self):
        if self.ser:
            self.ser.close()
            print("Connection closed.")

        self._stop_log_thread()

    def connected(self):
        return self.ser is not None

    def _start_log_thread(self):
        if self._log_thread and self._log_thread.is_alive():
            return
        self._log_thread_stop.clear()
        self._log_thread = threading.Thread(target=self._log_reader, daemon=True)
        self._log_thread.start()

    def _stop_log_thread(self):
        self._log_thread_stop.set()
        if self._log_thread:
            self._log_thread.join(timeout=2)
            self._log_thread = None

    def _log_reader(self):
        print("[ESP32] Serial log reader started.")
        pattern = re.compile(r"^(\d+\.?\d*)$")
        while not self._log_thread_stop.is_set() and self.ser:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    match = pattern.match(line)
                    if match:
                        currentTemp = float(match.group(1))
                        self.latest_temp_data = currentTemp
            except Exception as e:
                print(f"[ESP32] Log reader error: {e}")
            time.sleep(0.1)
        print("[ESP32] Serial log reader stopped.")

if __name__ == "__main__":
    esp32 = ESP32()

    esp32.move_z_arm_up()
    time.sleep(2)
    esp32.move_z_arm_down()
    esp32.close()