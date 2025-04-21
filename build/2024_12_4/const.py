
import logging
DOMAIN = "fire_camera"
IS_LOGGING = True
_LOGGER = logging.getLogger(__name__)


def log(message, type="info"):
    """Log message."""
    if IS_LOGGING:
        if type == "error":
            _LOGGER.error(message)
        elif type == "warning":
            _LOGGER.warning(message)
        elif type == "debug":
            _LOGGER.debug(message)
        else:
            _LOGGER.info(message)