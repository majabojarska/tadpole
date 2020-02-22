import math
import typing

from . import motor


class MotorController:
    """ Class for controlling front motors.

    Motor pins are defined as BCM GPIO indices.
    """

    SQRT_OF_TWO = math.sqrt(2)

    LEFT_MOTOR_POSITIVE_GPIO = 13
    LEFT_MOTOR_NEGATIVE_GPIO = 6
    RIGHT_MOTOR_POSITIVE_GPIO = 26
    RIGHT_MOTOR_NEGATIVE_GPIO = 19

    MAX_ABS_AXIS_VALUE = 2 ** 15

    def __init__(
        self,
        enable_throttle_curve: bool = False,
        throttle_gate_threshold: float = 0.1,
        throttle_scale: float = 1.0,
        throttle_limit: float = 1.0,
    ) -> None:
        """

        Parameters
        ----------
        enable_throttle_curve : bool
            If True, a throttle curve will be used.
        throttle_gate_threshold : float
            Threshold of the throttle gate.
            Throttle will be applied only if it exceeds this value.
        throttle_scale : float
            The value by which the throttle will be scaled.
        throttle_limit : float
            The maximum value throttle can achieve after applying all other modifiers.
        """
        self.left_motor = motor.Motor(
            self.LEFT_MOTOR_POSITIVE_GPIO,
            self.LEFT_MOTOR_NEGATIVE_GPIO,
            is_reversed=True,
        )
        self.right_motor = motor.Motor(
            self.RIGHT_MOTOR_POSITIVE_GPIO, self.RIGHT_MOTOR_NEGATIVE_GPIO
        )

        self.enable_throttle_curve = enable_throttle_curve

        self.throttle_gate_threshold = throttle_gate_threshold
        self.throttle_scale = throttle_scale
        self.throttle_limit = throttle_limit

    def handle_vector_input(self, input_vector: typing.Tuple[int, int]) -> None:
        """ Calculates and sets the throttle of both motors based on the input vector.

        Input vector processing chain is as follows:
        IN--->[Scale]->[Gate]->[Limit]--->OUT

        Parameters
        ----------
        input_vector : list
            A list of two integer values in the range of [0;65535].
        """
        angle = MotorController.calc_vector_angle(input_vector)
        left_motor_throttle_modifier = self.calc_left_throttle_mod(angle)
        right_motor_throttle_modifier = self.calc_right_throttle_mod(angle)
        throttle = self.throttle_scale * self.calc_normalized_vector_length(
            input_vector
        )

        if self.enable_throttle_curve:
            throttle = self._apply_throttle_curve(throttle)
        if self.throttle_gate_threshold is not None:
            throttle = self._apply_throttle_gate(throttle)
        if self.throttle_limit is not None:
            throttle = self._apply_throttle_limiting(throttle)

        left_motor_throttle = throttle * left_motor_throttle_modifier
        right_motor_throttle = throttle * right_motor_throttle_modifier

        self.left_motor.change_throttle(left_motor_throttle)
        self.right_motor.change_throttle(right_motor_throttle)

    def stop(self):
        """
        Stops both motors.

        :return: None
        """
        self.left_motor.stop()
        self.right_motor.stop()

    @staticmethod
    def calc_left_throttle_mod(joystick_angle: float) -> float:
        """ Calculates left motor throttle modifier.

        Function visualization: https://www.desmos.com/calculator/rhvsokblhl

        Parameters
        ----------
        joystick_angle : float
            The angle of the joystick with respect to the positive x axis.

        Returns
        -------
        throttle_modifier : float
            Throttle modifier for the left motor.
        """
        MotorController._assert_angle_within_range(joystick_angle)

        throttle_modifier = None
        if -180 < joystick_angle <= -90:
            throttle_modifier = -1.0
        elif -90 < joystick_angle < 0:
            throttle_modifier = joystick_angle / 45 + 1
        elif 0 <= joystick_angle <= 90:
            throttle_modifier = 1.0
        elif 90 < joystick_angle <= 180:
            throttle_modifier = -joystick_angle / 45 + 3

        return throttle_modifier

    @staticmethod
    def calc_right_throttle_mod(joystick_angle: float) -> float:
        """ Calculates right motor throttle modifier.

        Function visualization: https://www.desmos.com/calculator/xfo4g4fh4j

        Parameters
        ----------
        joystick_angle : float
            The angle of the joystick with respect to the positive x axis.

        Returns
        -------
        throttle_modifier : float
            Throttle modifier for the right motor.
        """

        MotorController._assert_angle_within_range(joystick_angle)

        throttle_modifier = None
        if -180 < joystick_angle < -90:
            throttle_modifier = -joystick_angle / 45 - 3
        elif -90 <= joystick_angle <= 0:
            throttle_modifier = -1.0
        elif 0 < joystick_angle < 90:
            throttle_modifier = joystick_angle / 45 - 1
        elif 90 <= joystick_angle <= 180:
            throttle_modifier = 1.0

        return throttle_modifier

    def calc_normalized_vector_length(
        self, input_vector: typing.Tuple[int, int]
    ) -> float:
        """ Calculates a normalized Euclidean vector length.

        Parameters
        ----------
        input_vector : tuple
            a tuple of two integer values representing a vector with
            initial point at (0,0) and a specified terminal point.

        Returns
        -------
        normalized_length : float
            Length of the normalized input vector.
        """

        assert type(input_vector) == tuple
        assert len(input_vector) == 2

        length = math.sqrt(input_vector[0] ** 2 + input_vector[1] ** 2)
        normalized_length = length / self.MAX_ABS_AXIS_VALUE
        if normalized_length > 1:
            normalized_length = 1

        return normalized_length

    @staticmethod
    def calc_vector_angle(input_vector: typing.Tuple[int, int]) -> float:
        """ Calculates the angle between the positive x axis and the input vector.

        Parameters
        ----------
        input_vector : tuple
            a tuple of two integer values representing a vector with
            initial point at (0,0) and a specified terminal point.

        Returns
        -------
        float
            vector angle as degrees in range (-180;180]
        """
        radians = math.atan2(input_vector[1], input_vector[0])
        return math.degrees(radians)

    @staticmethod
    def _assert_angle_within_range(angle: float) -> None:
        """ Asserts that the input angle is within a valid range of [-180;180) degrees.

        Parameters
        ----------
        angle : float
            Input angle.

        Raises
        ------
        ValueError
            If angle <= -180 or angle > 180.
        """
        if angle <= -180 or angle > 180:
            raise ValueError("Input angle is out of permitted range (-180;180]")

    @staticmethod
    def _apply_throttle_curve(throttle_modifier: float) -> float:
        """ Applies a throttle curve to the input throttle modifier.

        As an effect, this modifies sensitivity of the target motor to the input vector.

        Parameters
        ----------
        throttle_modifier : float
            Input throttle modifier.

        Returns
        -------
        new_throttle_modifier : float
            Resulting throttle modifier after mapping to a 3rd order polynomial curve.
        """
        a = 0
        b = 0.1666667
        c = 1.722222
        d = 0.5555556

        new_throttle_modifier = (
            a
            - b * throttle_modifier
            + c * throttle_modifier ** 2
            - d * throttle_modifier ** 3
        )

        if not 0 <= new_throttle_modifier <= 1:
            new_throttle_modifier = round(new_throttle_modifier)

        return new_throttle_modifier

    def _apply_throttle_gate(self, input_throttle: float):
        """ Calculates a gated throttle with respect to the gate threshold.

        Parameters
        ----------
        input_throttle : float
            The input throttle value.

        Returns
        -------
        float
            The gated throttle. Equals 0 for any value less than self.throttle_gate_threshold.
        """
        if abs(input_throttle) < self.throttle_gate_threshold:
            return 0
        return input_throttle

    def _apply_throttle_limiting(self, input_throttle: float):
        """
        Calculates a limited throttle with respect to the set limit.

        Parameters
        ----------
        input_throttle : float
            The input throttle value.

        Returns
        -------
        float
            The limited throttle value.
        """
        result_throttle = input_throttle

        if abs(input_throttle) > self.throttle_limit:
            result_throttle = self.throttle_limit
            result_throttle = math.copysign(result_throttle, input_throttle)
        return result_throttle
