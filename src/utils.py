import datetime
import logging
import os
import sys

from . import config


def setup_logger():
    """ Setup the Tadpole logger.

    Creates a log directory specified in the config file.
    Configures the logger.
    """
    log_dir_realpath = os.path.realpath(config.LOG_DIR)
    if not os.path.isdir(log_dir_realpath):
        os.makedirs(log_dir_realpath)

    log_name = "{}.log".format(datetime.datetime.now().strftime("%y-%m-%d_%H-%M-%S"))
    log_path = os.path.join(log_dir_realpath, log_name)

    logging.basicConfig(
        filename=log_path, format=config.LOGGER_FORMAT, level=logging.DEBUG
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
