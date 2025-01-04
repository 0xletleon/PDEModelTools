# log.py
import logging


def setup_logger():
    """配置日志"""
    logger = logging.getLogger("PMT")
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        # logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(name)s: %(levelname)s: %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger


log = setup_logger()
""" PMT 日志实例 """
