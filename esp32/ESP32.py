import serial
import time

class ESP32:
    def __init__(self, bt_port="COM8"):
        self.bt_port = bt_port
        self.ser = None

        def connect():
            try:
                print(f"Connecting to {self.bt_port}...")
                self.ser = serial.Serial(self.bt_port, 115200, timeout=2)
                time.sleep(2) # Give the connection a moment to settle
                print("Connection established.")
            except Exception as e:
                print(f"\nConnection Failed: {e}")
                print("Tip: Ensure the ESP32 is paired in your OS settings and the COM port is correct.")
                self.ser = None

        connect()

    def send_message(self, message, timeout=5):
        """
        Sends a string to ESP32 and waits for an 'ACK' response.
        Returns the response string if successful, None otherwise.
        """
        if self.ser is None:
            print("ESP32 not connected — cannot send message.")
            return None
        try:
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
            return True
        else:
            print("Failed to receive ACK from ESP32 for IRON_ON command.")
            return False
        
    def turn_off_soldering_iron(self):
        response = self.send_message("IRON_OFF")
        if response == "ACK: IRON_OFF":
            print(f"ESP32 Response: {response}")
            return True
        else:
            print("Failed to receive ACK from ESP32 for IRON_ON command.")
            return False
        
    def set_temp(self, temperature: int):
        response = self.send_message(f"SET_TEMP_{temperature}")
        if response == f"ACK: TEMP_SET {temperature}":
            print(f"ESP32 Response: {response}")
            return True
        else:
            print("Failed to receive ACK from ESP32 for SET_TEMP command.")
            return False

    def close(self):
        if self.ser:
            self.ser.close()
            print("Connection closed.")

    def connected(self):
        return self.ser is not None

if __name__ == "__main__":
    esp32 = ESP32()

    esp32.move_z_arm_up()
    time.sleep(2)
    esp32.move_z_arm_down()
    esp32.close()