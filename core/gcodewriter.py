""" This Python Class is used to translate user commands into gcode commands """

class GCodeWriter:
    # +z = up
    # -z = down
    # +x = right (facing front)
    # -x = left
    # +y = away? (facing front)
    # -y = towards

    def rapid_positioning(self, x: float | None , y: float | None):
        """ Moves the end effector in a straight line in the xy-plane. This will
        move the gantry at maximum speed (as defined by the hardware) """

        command = 'G0'
        if x is not None:
            command += f' X{x}'
        if y is not None:
            command += f' Y{y}'

        return command
    
    def linear_interpolation(self, x: float, y: float, f: float):
        """ Moves the end effector in a straight line in the xy-plane """

        command = 'G1'
        if x is not None:
            command += f' X{x}'
        if y is not None:
            command += f' Y{y}'
        if f is not None:
            command += f' F{f}'

        return command
    
    def move_up_down(self, z: float):
        """ Moves end effector up or down using rapid positioning """

        command = 'G0 '
        if z is not None:
            command += f'Z{z}'

        return command
    
    def wait(self, mil_sec: int):
        """" Pauses command queue for x milliseconds soldering to occur """

        command = f'G4 P{mil_sec}'

        return command

    def set_reference(self):
        """ Sets the current position as the reference point """

        command = 'G28.1'
        return command
    
    def set_workspace(self):
        command = 'G54'

        return command
    
    def set_zero_workspace(self):
        command = 'G10 L20 P1 X0 Y0 Z0'

        return command
    
    def reset(self):
        """ Moves end effector to reference point """

        # command = 'G28' - moves to machine home, which may not be the same as the reference point 
        command = 'G0 X0 Y0 Z0'
        return command
    
    def positioning(self, reference: str):
        """ Sets whether the coordinates should be interpreted relatively or 
        absolutely (absolute = with reference to zero, relative = with reference
        to current position) """

        if reference == "absolute":
            command = 'G90'
        elif reference == "relative":
            command = 'G91'
        
        return command
    
    def start_dispensing(self, speed: float):
        """ Turns the spool feed motor clockwise? to start dispensing solder 
        wire """
        
        command = f'M3 S{speed}'
        return command
    
    def retract_solder(self,speed: float):
        """ Turns the spool feed motor counter-clockwise? to retract solder
        wire """

        command = f'M4 S{speed}'
        return command
    
    def stop_dispensing(self):
        """ Stops the spool feed motor """
        
        command = 'M5'
        return command
    def velocity_to_feedrate(self, velocity):
        return f"F{velocity:.1f}"
    
    def home_axis_old(self, axis, all=False):
        """ Homes the specified axis ('x', 'y', or 'z') """

        print("Homing axis:", axis)
        command = 'G28 H'

        if all:
            return command
        if axis == 'x':
            command += ' X0'
        elif axis == 'y':
            command += ' Y0'
        elif axis == 'z':
            command += ' Z0'
        
        return command
    
    def home_axis(self, axis, all=False):
        """ Homes the specified axis ('x', 'y', or 'z') """

        command = '$H'  # Homing command for GRBL

        return command



