"""Gantry repeatability tests.

Move a RepeatabilityTester instance to a QThread before calling test slots,
the same way GCodeWorker is used in control_tab.py.
"""

import time
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from core.grbl_controller import GRBLController


class RepeatabilityTester(QObject):
    """Runs repeatability tests on the gantry.

    Signals
    -------
    log_requested(str)      : log message for the UI
    progress(int, int)      : (current_rep, total_reps)
    finished(str)           : emitted when a test completes; value is the test name
    """

    log_requested = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)

    def __init__(self, controller: GRBLController):
        super().__init__()
        self.controller = controller

    # ------------------------------------------------------------------
    # Test 1: Pen / marker dot cluster
    # ------------------------------------------------------------------

    @pyqtSlot(float, float, int, float, float)
    def run_dot_test(
        self,
        x: float,
        y: float,
        reps: int = 20,
        z_mark: float = -5.0,
        z_safe: float = 10.0,
    ):
        """Pen/marker dot repeatability test.

        Moves to (x, y) and lowers to z_mark for each rep, then raises to
        z_safe.  Mount a fine-tip marker in the nozzle holder and place
        paper on the bed.  Measure the resulting dot cluster diameter once
        the test finishes.

        Parameters
        ----------
        x, y   : target position in mm (workspace coords)
        reps   : number of dots to deposit (default 20)
        z_mark : Z height to lower to for contact (default -5.0 mm)
        z_safe : Z clearance height between marks (default 10.0 mm)
        """
        self.log_requested.emit(
            f"DOT TEST start — {reps} reps at X={x} Y={y} "
            f"(z_mark={z_mark} mm, z_safe={z_safe} mm)"
        )

        # Move to safe height before starting
        self.controller.send_commands([
            self.controller.writer.positioning("absolute"),
            self.controller.writer.set_workspace(),
            self.controller.writer.move_up_down(z_safe),
        ])

        for rep in range(1, reps + 1):
            self.log_requested.emit(f"  Rep {rep}/{reps}")
            self.progress.emit(rep, reps)

            self.controller.send_commands([
                self.controller.writer.positioning("absolute"),
                self.controller.writer.rapid_positioning(x, y),  # XY to target
                self.controller.writer.move_up_down(z_mark),     # lower to mark
                self.controller.writer.move_up_down(z_safe),     # raise for next rep
            ])

            time.sleep(0.5)  # brief pause between reps
            self.controller.send_commands([
            self.controller.writer.positioning("absolute"),
            self.controller.writer.rapid_positioning(0, 0),    
            ])
            time.sleep(0.5)  # brief pause after moving away

        self.log_requested.emit(
            "DOT TEST complete. Measure the dot cluster diameter on the paper."
        )
        self.finished.emit("dot_test")

    # ------------------------------------------------------------------
    # Test 2: Homing return
    # ------------------------------------------------------------------

    @pyqtSlot(float, float, int, float, float)
    def run_homing_return_test(
        self,
        x: float,
        y: float,
        reps: int = 10,
        backstep_mm: float = 10.0,
        pause_at_target: float = 1.0,
    ):
        """Dial gauge repeatability test.

        Homes all axes, moves to the dial gauge position (x, y), then
        repeatedly steps back backstep_mm and returns to (x, y) so you
        can read the gauge on each approach.

        Sequence:
          1. Home all axes
          2. Move to (x, y)
          3. For each rep:
               a. Move back backstep_mm in X (relative)
               b. Return to (x, y) (absolute)
               c. Dwell pause_at_target seconds — read the gauge

        Parameters
        ----------
        x, y             : dial gauge position in mm (workspace coords)
        reps             : number of back-and-forth cycles (default 10)
        backstep_mm      : how far to retract before each approach (default 10.0 mm)
        pause_at_target  : dwell at target each rep so the gauge can be read
                           (default 1.0 s)
        """
        self.log_requested.emit(
            f"DIAL GAUGE TEST start — {reps} reps at X={x} Y={y}, "
            f"backstep={backstep_mm} mm, dwell={pause_at_target} s"
        )

        # Home, then move to gauge position
        self.log_requested.emit("Homing all axes...")
        self.controller.send_commands(
            [self.controller.writer.home_axis(axis="all")]
        )

        self.log_requested.emit(f"Moving to gauge position X={x} Y={y}...")
        self.controller.send_commands([
            self.controller.writer.positioning("absolute"),
            self.controller.writer.set_workspace(),
            self.controller.writer.set_zero_workspace(),
            self.controller.writer.rapid_positioning(x, y),
        ])

        for rep in range(1, reps + 1):
            # Step back
            self.controller.send_commands([
                self.controller.writer.positioning("relative"),
                self.controller.writer.rapid_positioning(None, backstep_mm),
            ])
            
            # Dwell so the gauge can be read
            if pause_at_target > 0:
                time.sleep(pause_at_target)

            # Return to gauge position
            self.controller.send_commands([
                self.controller.writer.positioning("absolute"),
                self.controller.writer.rapid_positioning(x, y),
            ])

            self.log_requested.emit(f"  Rep {rep}/{reps} — read gauge now")
            self.progress.emit(rep, reps)

        self.log_requested.emit(
            f"DIAL GAUGE TEST complete ({reps} reps). "
            "Compare gauge readings across reps."
        )
        self.finished.emit("homing_return_test")
