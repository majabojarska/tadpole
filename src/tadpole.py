__author__ = "Maja Bojarska"

import logging
import threading

import RPi.GPIO as GPIO

from . import battery_guard
from . import gamepad
from . import motor_controller

logging.getLogger(__name__)


class Tadpole(threading.Thread):
    """ Class for controlling the Tadpole vehicle. """

    def __init__(self):
        super(Tadpole, self).__init__()

        self.motor_ctrl = motor_controller.MotorController()

        self.xbox_pad = gamepad.Gamepad(invert_y=True)
        self.xbox_pad.start()

        self.battery_guard = battery_guard.BatteryGuard()
        self.battery_guard.start()

    def __del__(self):
        GPIO.cleanup()

    def run(self):
        """ Main activity thread method. """
        while True:
            if not self.battery_guard.is_battery_ok:
                self.motor_ctrl.stop()
                logging.info("Battery low, switching to standby.")
                while not self.battery_guard.is_battery_ok:
                    self.xbox_pad.get_xy_vector_from_queue(block=True)

            new_xy_vector = self.xbox_pad.get_xy_vector_from_queue()
            if new_xy_vector:
                self.motor_ctrl.handle_vector_input(new_xy_vector)
