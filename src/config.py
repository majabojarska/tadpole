""" Configuration parameters for Tadpole setup. """

# Output of battery charging/discharge limiting module passed through
# a 10kohm/10kohm voltage divider. If this pin is HIGH, the module is
# outputting power, so the battery is still on a safe charge level.
# Once a discharge threshold is crossed, this pin becomes to LOW.
BATTERY_SENSE_PIN_GPIO = 5  # GPIO.BCM mode
LOW_BATTERY_TIMEOUT = 5  # Seconds
BATTERY_CHECK_PERIOD = 1  # Seconds

# Gamepad
DEFAULT_DEVICE_NAME = "Xbox Wireless Controller"
# DEFAULT_DEVICE_PATH = '/dev/input/event0'

# Logging
LOG_DIR = "log"
LOGGER_FORMAT = "%(asctime)s - %(message)s"
