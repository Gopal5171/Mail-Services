from logging.config import dictConfig


def init_log():
    LOGGING_CONFIG = {
        "version": 1,
        "loggers": {
            "": {  # root logger
                "level": "NOTSET",
                "handlers": [
                    "debug_console_handler",
                    "info_rotating_file_handler",
                    "error_file_handler",
                ],
            },
            "my.package": {
                "level": "WARNING",
                "propagate": False,
                "handlers": ["info_rotating_file_handler", "error_file_handler"],
            },
        },
        "handlers": {
            "debug_console_handler": {
                "level": "DEBUG",
                "formatter": "info",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "info_rotating_file_handler": {
                "level": "INFO",
                "formatter": "info",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/info.log",
                "mode": "a",
                "maxBytes": 1048576,
                "backupCount": 10,
            },
            "error_file_handler": {
                "level": "WARNING",
                "formatter": "error",
                "class": "logging.FileHandler",
                "filename": "logs/error.log",
                "mode": "a",
            },
        },
        "formatters": {
            "info": {
                "format": '%(asctime)s (%(filename)s:%(lineno)d %(threadName)s) %(levelname)s - %(name)s: "%(message)s"'
            },
            "error": {
                "format": '%(asctime)s (%(filename)s:%(lineno)d %(threadName)s) %(levelname)s - %(name)s: "%(message)s"'
            },
        },
    }
    dictConfig(LOGGING_CONFIG)
