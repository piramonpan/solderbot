""" This Python Class is used to translate user commands into gcode commands """

class GCodeWriter:

    def rapid_positioning(x, y) :
        """ Moves the end effector in a straight line in the xy-plane. This will
        move the gantry at maximum speed (as defined by the hardware) """

        command = 'G0'
        if x is not None:
            command += f' X{x}'
        if y is not None:
            command += f' Y{y}'

        return command
    
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
    
    def move_up_down(z):
        """ Moves end effector up or down using rapid positioning """

        command = 'G0 '
        if z is not None:
            command += f'Z{z:.3f}'

        return command

    def reset():
        """ Moves end effector to reference point """

        command = 'G28' # TO DO: how to set reference point/what is reference point?
        return command
    
    def positioning(reference):
        """ Sets whether the coordinates should be interpreted relatively or 
        absolutely (absolute = with reference to zero, relative = with reference
        to current position) """

        if reference is "absolute":
            command = 'G90'
        elif reference is "relative":
            command = 'G91'
        
        return command
    
    def velocity_to_feedrate(velocity):
        return f"F{velocity:.1f}"

