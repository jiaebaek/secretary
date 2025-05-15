import logging
from config import LOG_FILE_PATH

LOG_FILE = LOG_FILE_PATH
logger = logging.getLogger("trader")
logger.setLevel(logging.DEBUG)