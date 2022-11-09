import logging
import sys

from structlog import wrap_logger


def get_logger(name):
    logging.basicConfig(stream=sys.stdout)
    logger = logging.getLogger(name)
    logger.setLevel("INFO")

    logger = wrap_logger(logger)

    return logger
