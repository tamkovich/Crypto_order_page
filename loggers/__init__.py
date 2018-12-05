import logging


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler('loggers/' + name + "_log.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # console_handler = logging.StreamHandler()
    # console_handler.setFormatter(console_handler)
    # console_handler.setFormatter(formatter)
    # logger.addHandler(console_handler)

    return logger
