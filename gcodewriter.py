""" This Python Class is used to translate user commands into gcode commands """
# DEPRECATED: This file is a duplicate of core/gcodewriter.py and is no longer used.
# All imports should reference core.gcodewriter instead.

import functools
import warnings


def deprecated(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(f"{func.__name__} is deprecated and will be removed in a future version.", DeprecationWarning, stacklevel=2)
        return func(*args, **kwargs)
    return wrapper


class GCodeWriter:
    # +z = up
    # -z = down
    # +x = right (facing front)
    # -x = left
    # +y = away? (facing front)
    # -y = towards
    @deprecated
    def rapid_positioning(x, y) :
        """ Moves the end effector in a straight line in the xy-plane. This will
        move the gantry at maximum speed (as defined by the hardware) """

        command = 'G0'
        if x is not None:
            command += f' X{x}'
        if y is not None:
            command += f' Y{y}'

        return command
    
    @deprecated
    def linear_interpolation(x, y, f):
        """ Moves the end effector in a straight line in the xy-plane """

        command = 'G1'
        if x is not None:
            command += f' X{x}'
        if y is not None:
            command += f' Y{y}'
        if f is not None:
            command += f' F{f}'

        return command
    
    @deprecated
    def move_up_down(z):
        """ Moves end effector up or down using rapid positioning """

        command = 'G0 '
        if z is not None:
            command += f'Z{z}'

        return command
    
    @deprecated
    def wait(mil_sec):
        """" Pauses command queue for x milliseconds soldering to occur """

        command = f'G4 P{mil_sec}'

        return command

    @deprecated
    def set_reference():
        """ Sets the current position as the reference point """

        command = 'G28.1'
        return command
    
    @deprecated
    def reset():
        """ Moves end effector to reference point """

        command = 'G28'
        return command
    
    @deprecated
    def positioning(reference):
        """ Sets whether the coordinates should be interpreted relatively or 
        absolutely (absolute = with reference to zero, relative = with reference
        to current position) """

        if reference == "absolute":
            command = 'G90'
        elif reference == "relative":
            command = 'G91'
        
        return command
    
    @deprecated
    def velocity_to_feedrate(velocity):
        return f"F{velocity:.1f}"
    
    @deprecated
    def home_axis(axis, all=False):
        """ Homes the specified axis ('x', 'y', or 'z') """

        command = 'G28'
        if all:
            return command
        if axis == 'x':
            command += ' X0'
        elif axis == 'y':
            command += ' Y0'
        elif axis == 'z':
            command += ' Z0'
        
        return command
