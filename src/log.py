# log.py
import logging


def setup_logger() -> logging.Logger:
    """配置日志"""
    logger = logging.getLogger("PMT")
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        # logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(name)s.%(levelname)s: %(message)s"))
        logger.addHandler(handler)
    return logger


log: logging.Logger = setup_logger()
""" PMT 日志实例 """
