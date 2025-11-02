steps_per_revolution = 800
microsteps = 1/4
mm_per_rev = 2
steps_per_mm = (steps_per_revolution * microsteps) / mm_per_rev

robot_config = {
    "parameters":
        {
            "$0": 2,  # Step Pulse, us, CL57T has a 500 KHz max pulse input frequency
            "$21": 1,  # Hard limits boolean
            "$22": 1,  # Homing boolean -> see config.h for more advanced homing options
            "$24": 2000,  # Homing feed, mm/min
            "$27": 5,  # Homing pull-off, mm
            "$100": steps_per_mm,  # X, steps/mm
            "$101": steps_per_mm,  # Y, steps/mm
            "$102": steps_per_mm,  # Z, steps/mm
            "$110": 8000,  # X Max rate, mm/min
            "$111": 5000,  # Y Max rate, mm/min
            "$112": 8000,  # Z Max rate, mm/min
            "$120": 200,  # X Acceleration, mm/s^2
            "$121": 200,  # Y Acceleration, mm/s^2
            "$122": 200,  # Z Acceleration, mm/s^2
        }
}

single_axis_config = {
    "parameters":
        {
            "$0": 2,  # Step Pulse, us, CL57T has a 500 KHz max pulse input frequency
            "$21": 0,  # Hard limits boolean
            "$22": 1,   # Homing boolean -> see config.h for more advanced homing options
            "$24": 500,  # Homing feed, mm/min
            "$27": 2.5,  # Homing pull-off, mm
            "$100": steps_per_mm,  # Axis, steps/mm
            "$110": 8000,  # Axis Max rate, mm/min
            "$120": 200,  # Axis Acceleration, mm/s^2
        }
}
