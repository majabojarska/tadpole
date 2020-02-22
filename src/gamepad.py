import logging
import queue
import threading
from typing import Tuple, List, Optional

import evdev

from . import config

logging.getLogger(__name__)


class Gamepad(threading.Thread):
    """ Handles interfacing with evdev Xbox gamepad driver.

    Attributes
    ----------
    self._TIMEOUT_INF : int
        Timeout value that is considered to indicate infinite duration.
    self._TARGET_EVENT_TYPES : list of int
        Types of events that should be processed (not ignored).
    self._TARGET_EVENT_CODES : list of int
        Codes of events that should be processed (not ignored).
    timeout_connection : int
        Time from last received event, after which the gamepad connection
        times out.
    device : evdev.InputDevice
        Input device.
    _xy_vector_queue : queue.Queue
        Queue of XY stick position values from received events.
    last_event_values : dict
        Maps code of event to its respective value.
    invert_x : bool
        Defines inversion state of X axis.
        If True, the axis is inverted (in software).
    invert_y : bool
        Defines inversion state of Y axis.
        If True, the axis is inverted (in software).
    accept_every_nth_event : int
        Defines how often should events be interpreted. For a value of 3,
        1 event will be interpreted and the following 2 will be ignored.
        The reason for skipping events is that RPi Zero can't process all
        the incoming events without causing a noticeable input lag.
    """

    _TIMEOUT_INF = -1

    _TARGET_EVENT_TYPES = [3]

    _EVENT_CODE_RIGHT_X_AXIS = 2
    _EVENT_CODE_RIGHT_Y_AXIS = 5
    _EVENT_CODE_LEFT_X_AXIS = 0
    _EVENT_CODE_LEFT_Y_AXIS = 1

    _TARGET_EVENT_CODES = [_EVENT_CODE_RIGHT_X_AXIS, _EVENT_CODE_RIGHT_Y_AXIS]

    def __init__(
        self,
        device_path: str = None,
        device_name: str = config.DEFAULT_DEVICE_NAME,
        timeout_connection: int = _TIMEOUT_INF,
        accept_every_nth_event=1,
        invert_x=False,
        invert_y=False,
    ):
        """
        Parameters
        ----------
        device_path : str
            Path to target device. For example "/dev/input/event0".
        device_name : str
            Name of the target device
        timeout_connection : int
            Time from last received event, after which the gamepad connection
            times out.
        accept_every_nth_event : int
            Defines how often should events be interpreted. For a value of 3,
            1 event will be interpreted and the following 2 will be ignored.
            The reason for skipping events is that RPi Zero can't process all
            the incoming events without causing a noticeable input lag.
        invert_x : bool
            Defines inversion state of X axis.
            If True, the axis is inverted (in software).
        invert_y : bool
            Defines inversion state of Y axis.
            If True, the axis is inverted (in software).

        Raises
        ------
        ValueError
            If timeout_connection <= 0 and timeout_connection != TIMEOUT_INF.
        """
        super(Gamepad, self).__init__()

        if not (timeout_connection == self._TIMEOUT_INF or timeout_connection > 0):
            raise ValueError(
                "Connection timeout value must be greater than 0"
                " or equal to Gamepad.TIMEOUT_INF"
            )
        self.timeout_connection = timeout_connection

        self.device = self._get_device(device_path, device_name)
        self._xy_vector_queue = queue.Queue()

        self.last_event_values = {}
        for code in self._TARGET_EVENT_CODES:
            self.last_event_values[code] = 0

        self.invert_x = invert_x
        self.invert_y = invert_y
        self.accept_every_nth_event = accept_every_nth_event

    def run(self):
        """ Gamepad thread activity method. """
        received_event_count = 0
        while True:
            try:
                for event in self.device.read_loop():
                    received_event_count += 1
                    if (
                        received_event_count % self.accept_every_nth_event == 0
                        and event.type in self._TARGET_EVENT_TYPES
                        and event.code in self._TARGET_EVENT_CODES
                    ):
                        self.last_event_values[event.code] = event.value - 2 ** 15
                        self._xy_vector_queue.put(self._create_xy_vector())
            except OSError as e:
                print(e)
                self.device.close()
                self.device = self._get_device(device_name=config.DEFAULT_DEVICE_NAME)

    @staticmethod
    def _get_device(
        device_path: str = None, device_name: str = None
    ) -> evdev.InputDevice:
        """ Attempts to find and return a gamepad device matching the config.

        Parameters
        ----------
        device_path : str, optional
            Path to the target device.
        device_name : str, optional
            Name of the target device.

        Returns
        -------
        device : evdev.InputDevice
            The found gamepad device.

        Raises
        ------
        ValueError
            If both input parameters are None.
        """
        if not device_path and not device_name:
            ValueError("Must specify device_name or device_path.")

        if device_path is None:
            device_path = Gamepad._get_path_of_device_with_name(device_name, block=True)

        device = None
        while device is None:
            try:
                device = evdev.InputDevice(device_path)
            except (TypeError, FileNotFoundError) as err:
                pass

        return device

    @staticmethod
    def _get_path_of_device_with_name(
        device_name: str, block: bool = False
    ) -> Optional[str]:
        """ Attempts to find path to device with the specified device_name.

        Parameters
        ----------
        device_name : str
            Name of the target device.
        block : bool, optional
            If True, this function will run until a device with the specified
            device_name is found.
            If false, this function will return after the first attempt of
            finding the target device.

        Returns
        -------
        device_path : str or None
            The found device path. If a device with the specified name is not
            found, this value is None.
        """
        device_path = None

        while block is True and device_path is None:
            available_devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
            for device in available_devices:
                if device.name == device_name:
                    device_path = device.fn

        return device_path

    def get_xy_vector_from_queue(self, block=False) -> Optional[Tuple]:
        """ Calculates and returns a vector in a 2D plane (xy plane).

        The gamepad axes are inverted accordingly to the Gamepad object configuration.

        Parameters
        ----------
        block : bool
            If true, this function will wait until a vector is available in the
            _xy_vector_queue. Otherwise this function will return None.

        Returns
        -------
        tuple
            Tuple of two integers, representing a point in a 2D plane.
            None if _xy_vector_queue is empty.
        """
        try:
            vector = self._xy_vector_queue.get(block=block)
        except queue.Empty as e:
            return None

        if self.invert_x:
            vector[0] = vector[0] * -1
        if self.invert_y:
            vector[1] = vector[1] * -1

        return tuple(vector)

    def _create_xy_vector(self) -> List[int]:
        """ Creates a list containing the last received values of the right stick.

        The values' position in the returned list is (x, y).

        Returns
        -------
        list
            List of two integers, representing a point in a 2D plane.
        """
        return [
            self.last_event_values[self._EVENT_CODE_RIGHT_X_AXIS],
            self.last_event_values[self._EVENT_CODE_RIGHT_Y_AXIS],
        ]

    def _start_timeout_countdown(self) -> None:
        """ Starts connection timeout countdown. """
        raise NotImplementedError

    def flush_xy_vector_queue(self) -> None:
        """ Empties xy vector queue. """
        try:
            self.device.read()
        except (BlockingIOError, OSError):
            pass
