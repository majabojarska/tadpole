import logging

import RPi.GPIO as GPIO

logging.getLogger(__name__)


class Motor:
    """ Class for controlling a single motor over an H-bridge.

    Attributes
    ----------
    gpio_positive : int
        GPIO pin number of the positive motor control terminal.
    gpio_negative : int
        GPIO pin number of the negative motor control terminal.
    is_reversed : bool
        Defines whether the motor rotation direction is reversed.
    throttle : int
        Current throttle value.
    self.pwm_positive : int
        Current PWM value on gpio_positive pin.
    self.pwm_negative : int
        Current PWM value on gpio_negative pin.
    """

    def __init__(self, gpio_positive, gpio_negative, is_reversed=False):
        """
        Parameters
        ----------
        gpio_positive : int
            GPIO pin number of the positive motor control terminal.
        gpio_negative : int
            GPIO pin number of the negative motor control terminal.
        is_reversed : bool
            Defines whether the motor rotation direction is reversed.
        """
        self.gpio_positive = gpio_positive
        self.gpio_negative = gpio_negative
        self.is_reversed = is_reversed

        self.throttle = 0

        GPIO.setmode(GPIO.BCM)

        # Initialize and start PWM
        GPIO.setup(self.gpio_positive, GPIO.OUT)
        GPIO.setup(self.gpio_negative, GPIO.OUT)
        self.pwm_positive = GPIO.PWM(self.gpio_positive, 100)
        self.pwm_negative = GPIO.PWM(self.gpio_negative, 100)
        self.pwm_positive.start(0)
        self.pwm_negative.start(0)

    def __del__(self):
        """ Stops motor before object deletion """
        self.stop()

    def change_throttle(self, throttle) -> None:
        """ Sets a duty cycle based on the throttle parameter.

        Parameters
        ----------
        throttle : float
            New throttle value, between -1.0 and 1.0.
        """
        if self.is_reversed:
            throttle *= -1

        self.throttle = throttle

        abs_duty_cycle = round(abs(throttle) * 100)

        if throttle >= 0:
            self.pwm_positive.ChangeDutyCycle(abs_duty_cycle)
            self.pwm_negative.ChangeDutyCycle(0)
        else:
            self.pwm_positive.ChangeDutyCycle(0)
            self.pwm_negative.ChangeDutyCycle(abs_duty_cycle)

    def stop(self) -> None:
        """ Stops motor by setting both PWM duty cycles to 0 """
        logging.info("{} - Stopping motor".format(__name__))
        self.pwm_positive.ChangeDutyCycle(0)
        self.pwm_negative.ChangeDutyCycle(0)
