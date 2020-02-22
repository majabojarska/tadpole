import logging
import threading
import time

import RPi.GPIO as GPIO

from . import config

logging.getLogger(__name__)


class BatteryGuard(threading.Thread):
    """ Class for monitoring battery state and safety power management.

    Disables the motors if the battery sense pin shows a low-charge state.
    """

    def __init__(self):
        super(BatteryGuard, self).__init__()

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config.BATTERY_SENSE_PIN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        self.is_battery_ok = False
        self._last_ok_time = time.time()
        self._last_battery_state = 0

    def run(self):
        """ Main activity thread method. """
        while True:
            self._last_battery_state = GPIO.input(config.BATTERY_SENSE_PIN_GPIO)
            if self._last_battery_state == 1:
                self._last_ok_time = time.time()
                self.is_battery_ok = True
            elif (
                self._last_battery_state == 0
                and time.time() - self._last_ok_time > config.LOW_BATTERY_TIMEOUT
            ):
                self.is_battery_ok = False

            time.sleep(config.BATTERY_CHECK_PERIOD)
