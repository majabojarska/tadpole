import RPi.GPIO as GPIO

from . import tadpole
from . import utils

if __name__ == "__main__":
    GPIO.setwarnings(False)

    utils.setup_logger()

    tadpole_instance = tadpole.Tadpole()
    tadpole_instance.start()
