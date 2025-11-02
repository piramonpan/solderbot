class GcodeProcessor:
    @staticmethod
    def linear_interpolation_gcode(x, y, z):
        command = 'G1 '
        if x is not None:
            command += f"X{x:.6f} "
        if y is not None:
            command += f"Y{y:.6f} "
        if z is not None:
            command += f"Z{z:.6f} "

        return command

    @staticmethod
    def circular_interpolation_gcode(x, y, z, i, j, k, clockwise):
        command = "G2 " if clockwise else "G3 "
        if x is not None:
            command += f"X{x:.6f} "
        if y is not None:
            command += f"Y{y:.6f} "
        if z is not None:
            command += f"Z{z:.6f} "
        if i is not None:
            command += f"I{i:.6f} "
        if j is not None:
            command += f"J{j:.6f} "
        if k is not None:
            command += f"K{k:.6f} "

        return command

    @staticmethod
    def velocity_to_feedrate(velocity):
        return f"F{velocity:.1f}"

    @staticmethod
    def positioning(relative):
        if not relative:
            mode = "G90"
        else:
            mode = "G91"
        return mode
