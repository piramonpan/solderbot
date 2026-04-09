import sys
import logging
import time
import cv2
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QFrame,
    QGroupBox,
    QComboBox,
    QPlainTextEdit,
    QSpinBox,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap
from core.grbl_controller import GRBLController
import json
import os
from PyQt6.QtWidgets import QMessageBox, QLineEdit
import re
from esp32.ESP32 import ESP32

logger = logging.getLogger("SolderBot")


class GCodeWorker(QObject):
    log_requested = pyqtSignal(str)

    def __init__(self, gcode_controller: GRBLController, esp32=None):
        super().__init__()
        self.controller = gcode_controller
        self.esp32 = esp32

    @pyqtSlot(float, float, float)
    def execute_pan_test(self, x, y, z):
    # Go to a point relative to workspace that we set to zero
        if not self.controller:
            return
        self.log_requested.emit(f"Testing pan move to X:{x} Y:{y}, z:{z}")

        try:
            commands = [
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.set_workspace(),
                self.controller.writer.rapid_positioning(x=x, y=y),
                self.controller.writer.move_up_down(z=z)
            ]
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"Pan test error: {str(e)}")

    @pyqtSlot(str, float)
    def execute_jog(self, axis, step_size):
        if not self.controller:
            return
        self.log_requested.emit(f"Jogging {axis} by {step_size}")
        try:
            commands = [self.controller.writer.positioning(reference="relative")]
            x_val = step_size if axis == "X" else None
            y_val = step_size if axis == "Y" else None

            if axis in ["X", "Y"]:
                commands.append(
                    self.controller.writer.rapid_positioning(x=x_val, y=y_val)
                )
            elif axis == "Z":
                commands.append(self.controller.writer.move_up_down(z=step_size))
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_home(self):
        if not self.controller:
            return
        self.log_requested.emit("Homing all axes...")

        if self.esp32.connected():
            self.esp32.move_z_arm_down()
        else:
            self.log_requested.emit("ESP32 unavailable — skipping Z-arm lower before home.")
        try:
            command = self.controller.writer.home_axis(axis="all")
            self.controller.send_commands(commands=[command])
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_find_workspace(self):
        """Move to an estimated workspace location and set it as the new zero reference."""
        x_val = -78
        y_val = 69.8
        z_val = -10

        x_val = 59 + 4
        y_val = 112.5 - 4.6
        z_val = -20 - 8

        print(f"Using Z value from board_data.json: {z_val}")  # Debugging output

        commands = []

        if not self.controller:
            return
        self.log_requested.emit("Moving to workspace start...")
        try:
            # Simplified move logic based on your snippet
            commands.append(self.controller.writer.positioning(reference="relative"))
            commands.append(self.controller.writer.rapid_positioning(x=x_val, y=y_val))
            self.controller.send_commands(commands=commands)

            time.sleep(1)  # Give time for the move to complete

            commands = []
            commands.append(self.controller.writer.move_up_down(z=z_val))
            commands.append(self.controller.writer.set_workspace())
            commands.append(self.controller.writer.set_zero_workspace())
            self.controller.send_commands(commands=commands)

        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot(int, int)
    def execute_goto_grid(self, col, row):
        """Move to the given grid column and row."""
        if not self.controller:
            return
        self.log_requested.emit(f"GRID MOVE: Navigating to Column {col}, Row {row}")

        try:
            y_coord = col * -2.54 if col != 0 else 0
            x_coord = row * 2.54 if row != 0 else 0
            commands = [
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.set_workspace(),
                self.controller.writer.rapid_positioning(x=x_coord, y=y_coord),
            ]
            self.controller.send_commands(commands=commands)

        except Exception as e:
            self.log_requested.emit(f"Grid move error: {str(e)}")

    @pyqtSlot(int, int)
    def execute_goto_grid_2(self, col, row):
        """Move to grid position and dip Z for soldering."""
        if not self.controller:
            return
        self.log_requested.emit(f"GRID MOVE: Navigating to Column {col}, Row {row}")

        try:
            # Placeholder logic for grid navigation
            y_coord = col * -2.54 if col != 0 else 0
            x_coord = row * 2.54 if row != 0 else 0

            print(f"Row: {row}, Col: {col}")  # Debugging output
            print(f"Calculated grid coordinates: X={x_coord}, Y={y_coord}")  # Debugging output
    
            commands = [
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.set_workspace(),
                self.controller.writer.rapid_positioning(x=x_coord, y=y_coord),
                self.controller.writer.positioning(reference="relative"),
                self.controller.writer.rapid_positioning(x=1, y=None),
                self.controller.writer.move_up_down(z=-5),
                self.controller.writer.rapid_positioning(x=-1, y=None, z=-2),
            ]
            self.controller.send_commands(commands=commands)

        except Exception as e:
            self.log_requested.emit(f"Grid move error: {str(e)}")

    @pyqtSlot(float, float)
    def execute_custom_solder(self, extrude_time, hold_time):
        """Dispense solder using G4 dwell command."""
        if not self.controller:
            return
        self.log_requested.emit(
            f"SOLDER ACTION: Extruding Time: {extrude_time}s Solder Time: {hold_time}s"
        )

        try:
            commands = [
                self.controller.writer.start_dispensing(
                    speed=200
                ),  # HARD-CODED SPEED FOR TESTING
                self.controller.writer.wait(mil_sec=int(extrude_time * 1000)),
                self.controller.writer.stop_dispensing(),
                self.controller.writer.wait(
                    mil_sec=int(hold_time * 1000)
                ),  # Short wait after soldering
            ]
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot(float, float, float)
    def execute_custom_solder_2(self, extrude_time, hold_before, hold_time):
        """Dispense solder using Python-side delays."""
        if not self.controller:
            return
        self.log_requested.emit(
            f"SOLDER ACTION: Extruding Time: {extrude_time}s Solder Time: {hold_time}s"
        )
        try:
            commands = [
                str(hold_before),
                self.controller.writer.start_dispensing(
                    speed=200
                ),  # HARD-CODED SPEED FOR TESTING
                str(extrude_time),
                self.controller.writer.stop_dispensing(),
                str(hold_time)
            ]
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_return_to_start(self):
        print("DEBUG STARTTTTT")
        """Skeleton: Return to WORKSPACE origin"""
        self.log_requested.emit("RETURNING: Moving back to first spot...")
        if not self.controller:
            return
        try:
            commands = [
                self.controller.writer.positioning(reference="relative"),
                self.controller.writer.move_up_down(z=5),  # Move up for clearance
                self.controller.writer.set_workspace(),
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.rapid_positioning(x=0, y=0),
                self.controller.writer.move_up_down(
                    z=0
                ),  # Move back down to original z
            ]
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot(str)
    def execute_soldering_full(self, board_data_path):
        # line solder first
        self.execute_line_soldering(board_data_path)

        # point solder next
        self.execute_point_soldering(board_data_path)

        self.execute_clean()
        self.execute_return_to_start()
        self.log_requested.emit("Full soldering sequence complete!")

    @pyqtSlot(str)
    def execute_point_soldering(self, board_data_path):
        try:
            with open(board_data_path, 'r') as f:
                board_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log_requested.emit(f"Board data error: {e}")
            return

        self.log_requested.emit("Starting soldering sequence...")
        time.sleep(1)

        # Jog Z up before starting
        commands = [
            self.controller.writer.positioning(reference="relative"),
            self.controller.writer.move_up_down(z=7),
        ]
        self.controller.send_commands(commands=commands)

        counter = 0
        for point in board_data.get("points", []):
            row, col = point[0], point[1]
            if counter > 80:  # Clean tip every 20 holes
                self.execute_clean()
                counter = 0
                time.sleep(20)

            self.execute_goto_grid_2(row - 1, col - 1)
            self.execute_custom_solder_2(extrude_time=0.2, hold_time=2, hold_before=2)

            jog_cmds = [
                self.controller.writer.positioning(reference="relative"),
                self.controller.writer.rapid_positioning(x=1, y=None, z=2),
                self.controller.writer.move_up_down(z=5),
            ]
            self.controller.send_commands(commands=jog_cmds)
            counter += 1

        # Go back to start after finishing
        self.execute_return_to_start()

        self.log_requested.emit("Soldering sequence complete.")

    @pyqtSlot()
    def execute_soldering(self):
        if not self.controller:
            return
        self.log_requested.emit("Starting soldering sequence...")
        try:
            self.controller.start_soldering()
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_set_zero_workspace(self):
        print("DEBUG ZEROOOO")
        self.log_requested.emit("Setting current position as workspace zero...")
        if not self.controller:
            return
        try:
            command = self.controller.writer.set_zero_workspace()
            self.controller.send_commands(commands=[command])
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot(bool)
    def execute_extruding(self, extrude=True):
        if not self.controller:
            return
        self.log_requested.emit(
            "Extruding solder..." if extrude else "Stopping extrusion..."
        )
        try:
            if extrude:
                command = self.controller.writer.start_dispensing(
                    speed=200
                )  # HARD-CODED SPEED FOR TESTING
            else:
                command = self.controller.writer.stop_dispensing()
            self.controller.send_commands(commands=[command])
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")
    
    @pyqtSlot()
    def execute_clean(self):
        if not self.controller:
            return
        self.log_requested.emit("Cleaning soldering iron tip...")
        try:
            command = self.controller.clean_tip()
            self.controller.send_commands(commands=command)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_iron_on(self):
        if self.esp32 and self.esp32.connected():
            success = self.esp32.turn_on_soldering_iron()
            self.log_requested.emit("Soldering iron ON." if success else "Failed to turn ON soldering iron.")
        else:
            self.log_requested.emit("ESP32 not connected.")

    @pyqtSlot()
    def execute_iron_off(self):
        if self.esp32 and self.esp32.connected():
            success = self.esp32.turn_off_soldering_iron()
            self.log_requested.emit("Soldering iron OFF." if success else "Failed to turn OFF soldering iron.")
        else:
            self.log_requested.emit("ESP32 not connected.")

    @pyqtSlot(int)
    def execute_set_temp(self, temp: int):
        if self.esp32 and self.esp32.connected():
            success = self.esp32.set_temp(temp)
            self.log_requested.emit(f"Temperature set to {temp}°C." if success else "Failed to set temperature.")
        else:
            self.log_requested.emit("ESP32 not connected.")

    @pyqtSlot()
    def execute_take_image(self):
        """Move gantry to a safe overhead position for capturing an image."""
        if not self.controller:
            return
        self.log_requested.emit("Moving to image capture position...")
        try:
            commands = [
                self.controller.writer.set_workspace(),
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.move_up_down(z=10),
                self.controller.writer.rapid_positioning(x=-10, y=14),
            ]
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"Take image error: {str(e)}")

    @pyqtSlot()
    def execute_full_setup(self):
        """Run home  → find workspace -> probe Z sequentially in the worker thread."""
        if not self.controller:
            return

        # Step 1: Home
        self.log_requested.emit("Full setup (1/3): Homing all axes...")

        self.execute_home()
        # try:
        #     if self.esp32:
        #         self.esp32.move_z_arm_down()
        #     command = self.controller.writer.home_axis(axis="all")
        #     self.controller.send_commands(commands=[command])
        #     timeout, waited = 30, 0
        #     while waited < timeout:
        #         if "Idle" in self.controller.poll_grbl():
        #             break
        #         time.sleep(0.2)
        #         waited += 0.2
        # except Exception as e:
        #     self.log_requested.emit(f"Home error: {str(e)}")
        #     return
        
        # Step 2: Find Workspace
        self.log_requested.emit("Full setup (2/3): Finding workspace...")
        self.execute_find_workspace()

        # Step 3: Probe Z
        self.log_requested.emit("Full setup (3/3): Probing Z height...")
        self.execute_probe_z()

    @pyqtSlot(str)
    def execute_line_soldering(self, board_data_path):

        soldered_points = set()  # To track which points have been soldered for adhesion logic

        try:
            with open(board_data_path, 'r') as f:
                board_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log_requested.emit(f"Board data error: {e}")
            return

        self.log_requested.emit("Starting automated line soldering...")
        
        # Initial setup: Lift Z
        self.controller.send_commands([
            self.controller.writer.positioning(reference="relative"),
            self.controller.writer.move_up_down(z=7)
        ])

        for line in board_data.get("lines", []):
            rs, cs = line["start"]
            re, ce = line["end"]

            # Determine orientation automatically
            is_horiz = (cs != ce)
            solder_range = abs(cs - ce) + 1 if is_horiz else abs(rs - re) + 1
            
            # Shared Jog Command
            jog_up = [
                self.controller.writer.positioning(reference="relative"),
                self.controller.writer.rapid_positioning(x=1, y=None, z=2),
                self.controller.writer.move_up_down(z=5)
            ]

            for i in range(solder_range):
                # Calculate coordinates based on orientation
                curr_r = rs + (0 if is_horiz else i)
                curr_c = cs + (i if is_horiz else 0)
                
                self.execute_goto_grid_2(curr_r - 1, curr_c - 1)
                self.execute_custom_solder_2(
                    extrude_time=0.3, 
                    hold_time=0.5,
                    hold_before=0.2
                )
                self.controller.send_commands(jog_up)

                soldered_points.add((curr_r, curr_c))  # Track soldered point for adhesion logic
                if i == 0: 
                    continue # Adhesion logic

                # Mid-move logic: Horizontal uses X-axis offset, Vertical uses Y-axis
                y_val = -1.6 if is_horiz else 1.6

                self.controller.send_commands([
                    self.controller.writer.positioning(reference="relative"),
                    self.controller.writer.rapid_positioning(
                        x=(-1 + y_val) if is_horiz else -1, 
                        y=None if is_horiz else y_val
                    ),
                    self.controller.writer.move_up_down(z=-6.7)
                ])

                # Shimmy logic: Apply interpolation to the moving axis
                shimmy = [
                    self.controller.writer.start_dispensing(speed=180),
                    self.controller.writer.positioning(reference="relative")
                ]
                
                # Add movement steps based on axis
                if is_horiz:
                    shimmy.extend([
                        self.controller.writer.linear_interpolation(x=-0.5, y=None, f=600),
                        self.controller.writer.linear_interpolation(x=-0.5, y=None, f=600),
                        self.controller.writer.linear_interpolation(x=1.5, y=None, f=600)
                    ])
                else:
                    shimmy.extend([
                        self.controller.writer.linear_interpolation(x=None, y=0.5, f=600),
                        self.controller.writer.linear_interpolation(x=None, y=0.5, f=600),
                        self.controller.writer.linear_interpolation(x=None, y=-1.5, f=600)
                    ])


                shimmy.extend([self.controller.writer.stop_dispensing(),
                               self.controller.writer.move_up_down(z=-0.3)])
                
                self.controller.send_commands(shimmy)
                time.sleep(0.2)
                self.controller.send_commands(jog_up)
                time.sleep(0.2)
    
        self.execute_return_to_start()
        self.log_requested.emit("Soldering sequence complete.")

    @pyqtSlot(str)
    def execute_start_line_horizontal(self, board_data_path):
        try:
            with open(board_data_path, 'r') as f:
                board_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log_requested.emit(f"Board data error: {e}")
            return

        self.log_requested.emit("Starting line soldering sequence...")
        time.sleep(1)

        # Jog Z up before starting
        commands = [
            self.controller.writer.positioning(reference="relative"),
            self.controller.writer.move_up_down(z=7),
        ]
        self.controller.send_commands(commands=commands)

        counter = 0

        print("DEBUG: Starting line soldering with points:", board_data.get("lines", []))  # Debugging output
    
        for line in board_data.get("lines", []):
            row_s, col_s = line["start"][0], line["start"][1]
            row_e, col_e = line["end"][0], line["end"][1]

            for i in range(2):        
                # Solder beginning hole
                self.execute_goto_grid_2((row_s - 1), (col_s - 1 + i))
                self.execute_custom_solder_2(extrude_time=0.5,hold_before=0.2, hold_time=0.5)

                jog_up = [
                    self.controller.writer.positioning(reference="relative"),
                    self.controller.writer.rapid_positioning(x=1, y=None, z=2),
                    self.controller.writer.move_up_down(z=5),
                ]
                self.controller.send_commands(commands=jog_up)
                
                if i == 0:
                    continue # dont move to end hole on first iteration, just solder the start hole multiple times for better adhesion
                
                #DEBUG
                # Move +y 2.54/2 to midpoint between the two holes
                x_mid = ((row_s - 1) + (row_e - 1)) / 2.0 * 2.54
                y_mid = (2.54 / 2.0)  # Half the distance to move in Y to get to midpoint
                y_mid = -1.6  # Half the distance to move in Y to get to midpoint

                mid_move = [
                    self.controller.writer.positioning(reference="relative"),
                    self.controller.writer.rapid_positioning(x=-1+y_mid, y=None),
                    self.controller.writer.move_up_down(z=-6.7),
                ]
                self.controller.send_commands(commands=mid_move)

                # Hold for 3 sec then extrude 1 sec
                time.sleep(0.5)
                # self.execute_custom_solder_2(extrude_time=1.1, hold_time=0.2)

                shimmy = [
                    self.controller.writer.start_dispensing(speed=180),
                    self.controller.writer.positioning(reference="relative"),
                    self.controller.writer.linear_interpolation(x=-0.5, y=None, f=400),
                    self.controller.writer.linear_interpolation(x=-0.5, y=None, f=400),
                    self.controller.writer.linear_interpolation(x=1.2, y=None, f=400),
                    # self.controller.writer.linear_interpolation(x=None, y=-1, f=400),
                    self.controller.writer.move_up_down(z=-0.3),
                    self.controller.writer.stop_dispensing()
                ]

                self.controller.send_commands(commands=shimmy)
                # Wait 0.2 sec then immediately lift up
                time.sleep(0.2)
                self.controller.send_commands(commands=jog_up)
                time.sleep(0.5)

                counter += 1

        self.execute_return_to_start()

        self.log_requested.emit("Soldering sequence complete.")

    @pyqtSlot(str)
    def execute_start_line_vertical(self, board_data_path):
        try:
            with open(board_data_path, 'r') as f:
                board_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log_requested.emit(f"Board data error: {e}")
            return

        self.log_requested.emit("Starting line soldering sequence...")
        time.sleep(1)

        # Jog Z up before starting
        commands = [
            self.controller.writer.positioning(reference="relative"),
            self.controller.writer.move_up_down(z=7),
        ]
        self.controller.send_commands(commands=commands)

        counter = 0

        print("DEBUG: Starting line soldering with points:", board_data.get("lines", []))  # Debugging output
    
        for line in board_data.get("lines", []):
            row_s, col_s = line["start"][0], line["start"][1]
            row_e, col_e = line["end"][0], line["end"][1]

            solder_range = abs(row_s - row_e)

            # check that cols are the same for vertical line
            if col_s != col_e:
                self.log_requested.emit(f"Warning: For vertical line, column values must be the same. Got col_s={col_s}, col_e={col_e}. Using col_s for both.") 

            for i in range(solder_range + 1):        
                # Solder beginning hole
                self.execute_goto_grid_2((row_s - 1 + i), (col_s - 1))
                self.execute_custom_solder_2(extrude_time=0.3, hold_before=0.2, hold_time=0.2)

                jog_up = [
                    self.controller.writer.positioning(reference="relative"),
                    self.controller.writer.rapid_positioning(x=1, y=None, z=2),
                    self.controller.writer.move_up_down(z=5),
                ]
                self.controller.send_commands(commands=jog_up)
                
                if i == 0:
                    continue # dont move to end hole on first iteration, just solder the start hole multiple times for better adhesion
                
                #DEBUG
                y_mid = 1.6  # Half the distance to move in Y to get to midpoint

                mid_move = [
                    self.controller.writer.positioning(reference="relative"),
                    self.controller.writer.rapid_positioning(x=-1, y=y_mid),
                    self.controller.writer.move_up_down(z=-6.7),
                ]
                self.controller.send_commands(commands=mid_move)

                time.sleep(0.5)

                shimmy = [
                    self.controller.writer.start_dispensing(speed=180),
                    self.controller.writer.positioning(reference="relative"),
                    self.controller.writer.linear_interpolation(x=None, y=0.5, f=400),
                    self.controller.writer.linear_interpolation(x=None, y=0.5, f=400),
                    self.controller.writer.linear_interpolation(x=None, y=-1.2, f=400),
                    self.controller.writer.move_up_down(z=-0.3),
                    self.controller.writer.stop_dispensing()
                ]

                self.controller.send_commands(commands=shimmy)
                time.sleep(0.2)
                self.controller.send_commands(commands=jog_up)
                time.sleep(0.5)

                counter += 1

        self.execute_return_to_start()

        self.log_requested.emit("Soldering sequence complete.")


    @pyqtSlot()
    def execute_probe_z(self):

        self.log_requested.emit("Probing Z height...")
        try:
            commands = [
                self.controller.writer.set_workspace(),
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.rapid_positioning(x=None, y=None,z=20),
                self.controller.writer.rapid_positioning(x=78, y=-45),
            ]
            self.controller.send_commands(commands=commands)
            self.controller.send_commands(commands=[self.controller.writer.probe_z()])
            timeout, waited = 15, 0
            while waited < timeout:
                if "Idle" in self.controller.poll_grbl():
                    break
                time.sleep(0.2)
                waited += 0.2
        except Exception as e:
            self.log_requested.emit(f"Probe Z error: {str(e)}")
            return

        raw_data = self.controller.poll_grbl()
        match = re.search(r'MPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)', raw_data)
        z_val = float(match.group(3)) if match else None
        self.log_requested.emit(f"Probed Z: {z_val}" if z_val is not None else "Warning: could not parse Z")

        try:
            with open("board_data.json", "r") as f:
                board_data = json.load(f)
            board_data['first_hole'][2] = z_val
            with open("board_data.json", "w", encoding="utf-8") as f:
                json.dump(board_data, f, indent=2)
        except Exception as e:
            self.log_requested.emit(f"Error saving board data: {str(e)}")

        try:
            self.controller.send_commands(commands=[
                self.controller.writer.positioning(reference="relative"),
                self.controller.writer.move_up_down(z=10),
            ])
            time.sleep(1)
        except Exception as e:
            self.log_requested.emit(f"Z jog error: {str(e)}")

        if self.esp32:
            self.esp32.move_z_arm_up()

        # self.execute_return_to_start()

class JogControlPanel(QWidget):
    def __init__(self, parent_logger=None, compact=False):
        super().__init__()
        self.logger = parent_logger
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.init_ui(compact=compact)

    def init_ui(self, compact=False):
        # 1. Jog Grid
        jog_group = QGroupBox("Manual Movement")
        grid = QGridLayout()
        self.btn_y_pos = QPushButton("Y+")
        self.btn_y_neg = QPushButton("Y-")
        self.btn_x_pos = QPushButton("X+")
        self.btn_x_neg = QPushButton("X-")
        self.btn_z_pos = QPushButton("Z Up")
        self.btn_z_neg = QPushButton("Z Down")

        grid.addWidget(self.btn_y_pos, 0, 1)
        grid.addWidget(self.btn_x_neg, 1, 0)
        grid.addWidget(self.btn_x_pos, 1, 2)
        grid.addWidget(self.btn_y_neg, 2, 1)
        grid.addWidget(self.btn_z_pos, 0, 3)
        grid.addWidget(self.btn_z_neg, 2, 3)

        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("Step:"))
        self._step_btns = []
        for val in ("0.1", "0.5", "1", "2.54", "5", "10"):
            btn = QPushButton(val)
            btn.setCheckable(True)
            btn.setFixedWidth(52)
            btn.setObjectName("btn_step_size")
            btn.clicked.connect(lambda _, v=val: self._select_step(v))
            step_layout.addWidget(btn)
            self._step_btns.append((val, btn))
        step_layout.addStretch()
        self._current_step = "1"
        self._step_btns[2][1].setChecked(True)  # default: 1 mm
        grid.addLayout(step_layout, 3, 0, 1, 4)

        self.btn_set_zero = QPushButton("Set Zero")
        self.btn_set_zero.setObjectName("btn_action_accent")
        grid.addWidget(self.btn_set_zero, 0, 4)

        self.btn_return_start = QPushButton("Return")
        self.btn_return_start.setObjectName("btn_back_nav")
        grid.addWidget(self.btn_return_start, 2, 4)

        jog_group.setLayout(grid)

        # 2. Grid Selection (NEW)
        grid_nav_group = QGroupBox("Grid Navigation")
        grid_nav_layout = QHBoxLayout()
        self.spin_col = QSpinBox()
        self.spin_col.setRange(0, 100)
        self.spin_row = QSpinBox()
        self.spin_row.setRange(0, 100)
        self.btn_grid_go = QPushButton("GO")
        grid_nav_layout.addWidget(QLabel("Row:"))
        grid_nav_layout.addWidget(self.spin_col)
        grid_nav_layout.addWidget(QLabel("Col:"))
        grid_nav_layout.addWidget(self.spin_row)
        grid_nav_layout.addWidget(self.btn_grid_go)
        grid_nav_group.setLayout(grid_nav_layout)

        # 3. Custom Solder Control (NEW)
        self.solder_group = QGroupBox("Solder Parameters")
        solder_layout = QGridLayout()
        self.spin_extrude = QDoubleSpinBox()
        self.spin_extrude.setSuffix(" s")
        self.spin_time = QDoubleSpinBox()
        self.spin_time.setSuffix(" s")
        self.btn_solder = QPushButton("Solder")

        solder_layout.addWidget(QLabel("Extrude Time:"), 0, 0)
        solder_layout.addWidget(self.spin_extrude, 0, 1)
        solder_layout.addWidget(QLabel("Solder Time:"), 1, 0)
        solder_layout.addWidget(self.spin_time, 1, 1)
        solder_layout.addWidget(self.btn_solder, 2, 0, 1, 2)
        self.solder_group.setLayout(solder_layout)

        self.layout.addWidget(jog_group)
        if not compact:
            self.layout.addWidget(grid_nav_group)
            self.layout.addWidget(self.solder_group)

    def _select_step(self, value: str):
        for val, btn in self._step_btns:
            btn.setChecked(val == value)
        self._current_step = value

    @property
    def step_size(self):
        return self._current_step


class ControlTab(QWidget):
    request_jog = pyqtSignal(str, float)
    request_home = pyqtSignal()
    request_first = pyqtSignal()
    request_soldering = pyqtSignal()
    # New Signals
    request_set_zero_workspace = pyqtSignal()
    request_grid_move = pyqtSignal(int, int)
    request_custom_solder = pyqtSignal(float, float, float)
    request_return_start = pyqtSignal()
    request_extruding = pyqtSignal(bool)
    request_clean = pyqtSignal()
    request_first_hole_pan = pyqtSignal(float, float, float)
    request_full_setup = pyqtSignal()
    request_start_soldering_sequence = pyqtSignal(str)

    def __init__(self, logger=logger, gcode_controller=None, esp32_controller=None, testing=True):
        super().__init__()
        self.gcode_controller = gcode_controller
        self.logger = logger
        self.worker = None
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(25)

        self.esp32: ESP32 = esp32_controller

        self.init_ui()

        # Threads
        self.camera_worker = CameraWorker()
        self.camera_worker.frame_received.connect(self.update_label)
        self.camera_worker.start()

        self.gcode_thread = QThread()
        self.worker = GCodeWorker(self.gcode_controller, esp32=self.esp32)
        self.worker.moveToThread(self.gcode_thread)

        # Connect signals to worker slots 
        self.request_jog.connect(self.worker.execute_jog)
        self.request_home.connect(self.worker.execute_home)
        self.request_first.connect(self.worker.execute_find_workspace)
        self.request_soldering.connect(self.worker.execute_soldering)
        self.request_grid_move.connect(self.worker.execute_goto_grid)
        self.request_custom_solder.connect(self.worker.execute_custom_solder_2)
        self.request_return_start.connect(self.worker.execute_return_to_start)
        self.request_set_zero_workspace.connect(
            self.worker.execute_set_zero_workspace
        )
        self.request_extruding.connect(self.worker.execute_extruding)
        self.request_clean.connect(self.worker.execute_clean)
        self.request_first_hole_pan.connect(self.worker.execute_pan_test)
        self.request_full_setup.connect(self.worker.execute_full_setup)
        self.request_start_soldering_sequence.connect(self.worker.execute_start_soldering_sequence)
        self.worker.log_requested.connect(lambda msg: self.logger.info(msg))

        self.gcode_thread.start()
        self.connect_buttons()

        self.jog_widget.setEnabled(True)
        self.btn_return_start.setEnabled(True)
        self.btn_set_zero.setEnabled(True)
        self.go_first.setEnabled(True)

    def init_ui(self):
        # LEFT COLUMN
        left_panel = QVBoxLayout()
        self.camera_feed = QFrame()
        self.camera_feed.setMinimumSize(640, 480)
        self.camera_feed.setStyleSheet("background-color: #000; border-radius: 15px;")
        feed_layout = QVBoxLayout(self.camera_feed)
        self.primary_feed = QLabel("PRIMARY CAMERA FEED")
        self.primary_feed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        feed_layout.addWidget(self.primary_feed)

        self.zoom_feed = QLabel(self.primary_feed)
        self.zoom_feed.setFixedSize(160, 120)
        self.zoom_feed.setStyleSheet(
            "background-color: #1C1C1E; border: 2px solid #007AFF; border-radius: 4px;"
        )
        self.zoom_feed.move(0, 10)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        left_panel.addWidget(self.camera_feed, stretch=3)
        left_panel.addWidget(QLabel("SYSTEM LOG"))
        left_panel.addWidget(self.log_output, stretch=1)

        # RIGHT COLUMN
        right_panel = QVBoxLayout()
        self.jog_widget = JogControlPanel(parent_logger=self.logger)

        progress_group = QGroupBox("Mission Progress")
        prog_layout = QVBoxLayout()
        self.p_bar = QProgressBar()
        self.status_label = QLabel("Ready to initialize...")
        prog_layout.addWidget(self.p_bar)
        prog_layout.addWidget(self.status_label)
        progress_group.setLayout(prog_layout)

        # --- Gantry Setup Group ---
        setup_group = QGroupBox("Gantry Setup")
        setup_layout = QVBoxLayout()
        setup_layout.setSpacing(5)
        self.home_start = QPushButton("Home")
        self.go_first = QPushButton("Find Workspace")
        self.btn_set_zero = QPushButton("Set Zero")
        self.btn_return_start = QPushButton("Return to Start")
        self.btn_probe_z = QPushButton("Probe Z")
        self.btn_full_setup = QPushButton("Full Setup (Home → Probe → Workspace)")
        for btn in [self.home_start, self.go_first, self.btn_set_zero,
                    self.btn_return_start, self.btn_probe_z, self.btn_full_setup]:
            setup_layout.addWidget(btn)
        setup_group.setLayout(setup_layout)

        # --- Dispensing Group ---
        disp_group = QGroupBox("Other Util")
        disp_layout = QVBoxLayout()
        disp_layout.setSpacing(5)
        self.btn_clean = QPushButton("Clean Tip")
        self.btn_extrude = QPushButton("Pan to First Hole")
        self.btn_stop_extrude = QPushButton("Stop Extrude")
        for btn in [self.btn_clean, self.btn_extrude, self.btn_stop_extrude]:
            disp_layout.addWidget(btn)
        disp_group.setLayout(disp_layout)

        
        # --- Temperature Control Group ---
        temp_group = QGroupBox("Temperature Control")
        temp_layout = QVBoxLayout()
        # Live temperature label
        self.label_live_temp = QLabel("Current Temp: --- °C")
        self.label_live_temp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        temp_layout.addWidget(self.label_live_temp)
        self.btn_iron_on = QPushButton("Iron On")
        self.btn_iron_off = QPushButton("Iron Off")
        temp_btn_layout = QHBoxLayout()
        temp_btn_layout.addWidget(self.btn_iron_on)
        temp_btn_layout.addWidget(self.btn_iron_off)
        temp_layout.addLayout(temp_btn_layout)
        temp_set_layout = QHBoxLayout()
        self.edit_temp = QLineEdit()
        self.edit_temp.setPlaceholderText("300")
        self.btn_set_temp = QPushButton("Set Temp")
        temp_set_layout.addWidget(QLabel("Set Temperature:"))
        temp_set_layout.addWidget(self.edit_temp)
        temp_set_layout.addWidget(QLabel("°C"))
        temp_set_layout.addWidget(self.btn_set_temp)
        temp_layout.addLayout(temp_set_layout)
        temp_group.setLayout(temp_layout)

        # Reserved / inactive buttons (wired in connect_buttons)
        self.btn_start = QPushButton("Start Sequence")
        self.btn_stop = QPushButton("Emergency Stop")
        self.start_soldering_sequence = QPushButton("Start Soldering")
        self.start_soldering_sequence.setObjectName("btn_start")

        right_panel.addWidget(self.jog_widget)
        right_panel.addWidget(setup_group)
        right_panel.addWidget(temp_group)
        right_panel.addWidget(disp_group)
        right_panel.addStretch()
        right_panel.addWidget(self.start_soldering_sequence)

        self.main_layout.addLayout(left_panel, stretch=2)
        self.main_layout.addLayout(right_panel, stretch=1)

        # Timer for updating live temperature
        from PyQt6.QtCore import QTimer
        self.temp_timer = QTimer(self)
        self.temp_timer.timeout.connect(self.update_live_temp)
        self.temp_timer.start(500)  # update every 500 ms

    def update_live_temp(self):
        if self.esp32 and getattr(self.esp32, 'latest_temp_data', None):
            currentTemp = self.esp32.latest_temp_data
            self.label_live_temp.setText(f"Current Temp: {currentTemp} °C")
        else:
            self.label_live_temp.setText("Current Temp: --- °C")

    def connect_buttons(self):
        # Jogging
        self.jog_widget.btn_x_pos.clicked.connect(lambda: self.issue_jog("X", 1))
        self.jog_widget.btn_x_neg.clicked.connect(lambda: self.issue_jog("X", -1))
        self.jog_widget.btn_y_pos.clicked.connect(lambda: self.issue_jog("Y", 1))
        self.jog_widget.btn_y_neg.clicked.connect(lambda: self.issue_jog("Y", -1))
        self.jog_widget.btn_z_pos.clicked.connect(lambda: self.issue_jog("Z", 1))
        self.jog_widget.btn_z_neg.clicked.connect(lambda: self.issue_jog("Z", -1))

        # New Feature Buttons
        self.jog_widget.btn_grid_go.clicked.connect(self.issue_grid_move)
        self.jog_widget.btn_solder.clicked.connect(self.issue_custom_solder)
        self.jog_widget.btn_set_zero.clicked.connect(self.issue_set_zero_workspace)
        self.btn_set_zero.clicked.connect(self.issue_set_zero_workspace)
        self.btn_return_start.clicked.connect(lambda: self.request_return_start.emit())

        # Action Buttons
        self.btn_clean.clicked.connect(self.clean_button_clicked)
        self.btn_extrude.clicked.connect(self.extrude_button_clicked)
        self.home_start.clicked.connect(self.home_button_clicked)
        self.start_soldering_sequence.clicked.connect(self.start_soldering_sequence_clicked)
        self.btn_probe_z.clicked.connect(self.probe_z_clicked)
        self.go_first.clicked.connect(self.find_workspace_button_clicked)
        self.btn_stop_extrude.clicked.connect(self.stop_extrude_button_clicked)
        self.btn_full_setup.clicked.connect(lambda: self.request_full_setup.emit())

        self.btn_start.clicked.connect(lambda: self.request_soldering.emit())

        # Temperature Control Buttons
        self.btn_iron_on.clicked.connect(self.iron_on_clicked)
        self.btn_iron_off.clicked.connect(self.iron_off_clicked)
        self.btn_set_temp.clicked.connect(self.set_temp_clicked)

    def iron_on_clicked(self):
        if self.esp32 and self.esp32.connected():
            success = self.esp32.turn_on_soldering_iron()
            if success:
                self.logger.info("Soldering iron turned ON.")
            else:
                self.logger.error("Failed to turn ON soldering iron.")
        else:
            self.logger.error("ESP32 not connected.")

    def iron_off_clicked(self):
        if self.esp32 and self.esp32.connected():
            success = self.esp32.turn_off_soldering_iron()
            if success:
                self.logger.info("Soldering iron turned OFF.")
            else:
                self.logger.error("Failed to turn OFF soldering iron.")
        else:
            self.logger.error("ESP32 not connected.")

    def set_temp_clicked(self):
        if self.esp32 and self.esp32.connected():
            temp_text = self.edit_temp.text().strip()
            try:
                temp = int(temp_text)
            except ValueError:
                self.logger.error("Invalid temperature input. Please enter a number.")
                return
            success = self.esp32.set_temp(temp)
            if success:
                self.logger.info(f"Set soldering iron temperature to {temp}°C.")

    def issue_jog(self, axis, direction):
        step = float(self.jog_widget.step_size) * direction
        self.request_jog.emit(axis, step)

    def issue_grid_move(self):
        col = self.jog_widget.spin_col.value()
        row = self.jog_widget.spin_row.value()
        self.request_grid_move.emit(col, row)

    def issue_custom_solder(self):
        ext = self.jog_widget.spin_extrude.value()
        sec = self.jog_widget.spin_time.value()
        self.request_custom_solder.emit(ext, sec, sec)

    def issue_set_zero_workspace(self):
        self.request_set_zero_workspace.emit()

    def log(self, msg: str, level: int):
        import logging as _logging
        if level >= _logging.ERROR:
            self.log_output.appendHtml(f'<span style="color:#FF3B30;">{msg}</span>')
        elif level >= _logging.WARNING:
            self.log_output.appendHtml(f'<span style="color:#FF9500;">{msg}</span>')
        else:
            self.log_output.appendPlainText(msg)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def update_label(self, q_image):
        pixmap = QPixmap.fromImage(q_image)
        self.primary_feed.setPixmap(
            pixmap.scaled(self.primary_feed.size(), Qt.AspectRatioMode.KeepAspectRatio)
        )

        # Zoom feed: crop 1/10 of the frame around the crosshair center and scale to zoom_feed size
        img_w = q_image.width()
        img_h = q_image.height()
        crop_w = max(1, img_w // 10)
        crop_h = max(1, img_h // 10)
        cx = img_w // 2 + 230
        cy = img_h // 2 - 155
        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        cropped = pixmap.copy(x1, y1, crop_w, crop_h)
        self.zoom_feed.setPixmap(
            cropped.scaled(self.zoom_feed.size(), Qt.AspectRatioMode.KeepAspectRatio)
        )

        # Keep zoom_feed anchored to top-left of primary_feed and on top
        margin = 8
        self.zoom_feed.move(margin, margin)
        self.zoom_feed.raise_()

    def find_workspace_button_clicked(self):
        self.logger.info("Finding workspace...")
        self.go_first.setEnabled(True)
        self.btn_return_start.setEnabled(True)
        self.btn_set_zero.setEnabled(True)
        self.jog_widget.setEnabled(True)
        self.request_first.emit()

    def home_button_clicked(self):
        self.logger.info("Homing robot...")
        self.go_first.setEnabled(True)
        self.btn_return_start.setEnabled(True)
        self.btn_set_zero.setEnabled(True)
        self.jog_widget.setEnabled(True)

        if self.esp32.connected():
            self.esp32.move_z_arm_down()
        else:
            self.logger.warning("ESP32 unavailable — skipping Z-arm lower before home.")

        self.request_home.emit()

    def probe_z_clicked(self):
        print("Probing Z height...")

        x_val = 136
        y_val = 36
        commands = [self.worker.controller.writer.positioning(reference="relative"),
                    self.worker.controller.writer.rapid_positioning(x=x_val, y=y_val)]

        self.worker.controller.send_commands(commands=commands)

        if not self.worker:
            return
        self.worker.log_requested.emit("Probing Z height...")
        try:
            command = self.worker.controller.writer.probe_z()
            self.worker.controller.send_commands(commands=[command])

            # Wait for probe_z() G-code to finish by polling for 'Idle' state
            timeout = 15  # seconds
            waited = 0
            while waited < timeout:
                status = self.worker.controller.poll_grbl()
                if "Idle" in status:
                    break
                time.sleep(0.2)
                waited += 0.2
        except Exception as e:
            self.worker.log_requested.emit(f"G-Code Error: {str(e)}")
            return

        raw_data = self.worker.controller.poll_grbl()
        match = re.search(r'MPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)', raw_data)
        print(match)

        if match:
            # The third capturing group is our Z value
            z_val = float(match.group(3))
            print("Probed Z value:", z_val)
        else:
            z_val = None

        # Save z_val to example_board.json
        filename = "board_data.json"
        try:
            with open(filename, "r") as f:
                board_data = json.load(f)
        except Exception as e:
            print("Error loading example_board.json:", e)
            board_data = {}

        board_data['first_hole'][2] = z_val
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(board_data, f, indent=2)
            print(f"Saved probed_z={z_val} to example_board.json")
        except Exception as e:
            print("Error saving example_board.json:", e)

        self.request_jog.emit("Z", 10)
        time.sleep(1)
        self.esp32.move_z_arm_up()
        pass
        
    def clean_button_clicked(self):
        self.logger.info("Cleaning soldering iron tip and extruding...")
        self.request_clean.emit()
        self.request_extruding.emit(False)

    def extrude_button_clicked(self):
        try:
            x, y, z = self.find_first_hole()
            self.request_first_hole_pan.emit(x, -y, z)
        except Exception as e:
            self.logger.error(f"Pan to first hole failed: {e}")

    def stop_extrude_button_clicked(self):
        self.logger.info("Stopping extrusion...")
        self.request_extruding.emit(False)

    def find_first_hole(self):
        try:
            with open("board_data.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            self.logger.error("board_data.json not found — cannot locate first hole.")
            return 0.0, 0.0, 0.0
        except json.JSONDecodeError as e:
            self.logger.error(f"board_data.json is malformed: {e}")
            return 0.0, 0.0, 0.0

        pixel_first_hole_x = data.get("first_hole", [0, 0])[0]
        pixel_first_hole_y = data.get("first_hole", [0, 0])[1]
        z_val = data.get("first_hole", [0, 0])[2] + 10

        print("moving down from z:", z_val)
        
        pixel_home_x, pixel_home_y = data.get("camera_pixel_zero", [0, 0])
        pixel_mm_ratio = data.get("pixel_mm_ratio", 9.36)

        if not pixel_mm_ratio:
            self.logger.error("pixel_mm_ratio is zero — cannot calculate real-world coordinates.")
            return 0.0, 0.0, 0.0

        first_hole_move_x = round((pixel_first_hole_x - pixel_home_x) / pixel_mm_ratio, 2)
        first_hole_move_y = round((pixel_first_hole_y - pixel_home_y) / pixel_mm_ratio, 2)
        self.logger.info(f"First hole offset: X={first_hole_move_x}mm, Y={first_hole_move_y}mm")
        return first_hole_move_x, first_hole_move_y, z_val
        

    def start_soldering_sequence_clicked(self):
        if not self.worker:
            self.logger.warning("No GRBL worker available — cannot start sequence.")
            return

        board_data_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../board_data.json')
        )
        self.request_start_soldering_sequence.emit(board_data_path)

    def wait_for_user(self, msg):
            # for testing purposes only
            dlg = QMessageBox()
            dlg.setWindowTitle("Continue?")
            dlg.setText(msg)
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()

import cv2
import time
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

class CameraWorker(QThread):
    frame_received = pyqtSignal(QImage)

    def __init__(self):
        super().__init__()
        self.is_paused = False

    def run(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        cap.set(cv2.CAP_PROP_FPS, 30)

        if not cap.isOpened():
            print("CameraWorker: failed to open camera index 0.")
            return

        while self.isRunning():
            if self.is_paused:
                cap.release()
                while self.is_paused and self.isRunning():
                    time.sleep(0.1)
                if not self.isRunning():
                    break
                cap.open(0, cv2.CAP_DSHOW)
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
                cap.set(cv2.CAP_PROP_FPS, 30)
                continue

            ret, frame = cap.read()
            if ret:
                # 2. Define center based on actual frame size
                h, w, ch = frame.shape
                center = ((w // 2) + 230, (h // 2) - 160)
                radius = 10
                color = (0, 0, 255)  # BGR Red
                thickness = 2

                # 3. DRAW FIRST (on the NumPy array)
                # cv2.circle(frame, center, radius, color, thickness)

                # 4. CONVERT SECOND (BGR to RGB for Qt)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # 5. Create QImage
                bytes_per_line = ch * w
                qt_img = QImage(
                    rgb_frame.data, 
                    w, 
                    h, 
                    bytes_per_line, 
                    QImage.Format.Format_RGB888
                )

                # Emit a copy to ensure the memory stays valid in the main thread
                self.frame_received.emit(qt_img.copy())

            # Adjust sleep to hit roughly 30 FPS
            time.sleep(0.01)

        cap.release()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ControlTab(testing=True)
    window.show()
    sys.exit(app.exec())