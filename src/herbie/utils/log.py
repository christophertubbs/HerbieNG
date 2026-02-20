"""
Log classes and helpers for the application
"""
import logging
import logging.config
import logging.handlers
import pathlib
import threading

from herbie.configuration import settings

_SETUP_LOCK: threading.RLock = threading.RLock()


class LevelRangeFilter(logging.Filter):
    """
    A filter that constrains messages to a minimum and maximum level, inclusive
    """
    def __init__(self, minimum: int | str = logging.DEBUG, maximum: int | str = logging.CRITICAL, name: str = ""):
        super().__init__(name=name)
        self.__minimum: int = logging.getLevelName(minimum) if isinstance(minimum, str) else minimum
        self.__maximum: int = logging.getLevelName(maximum) if isinstance(maximum, str) else maximum

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Whether the record of the message falls within the range
        """
        return self.__minimum <= record.levelno <= self.__maximum


def setup_logging():
    with _SETUP_LOCK:
        if len(logging.root.handlers) > 0:
            return
        import json

        if settings.log_config_path.is_file():
            configuration: dict = json.loads(settings.log_config_path.read_text())
            logging.config.dictConfig(configuration)
            if settings.debug:
                logging.root.setLevel(logging.DEBUG)
            else:
                logging.root.setLevel(logging.INFO)
        else:
            logging.basicConfig(
                level=logging.DEBUG if settings.debug else logging.INFO,
                format="[%(asctime)s] %(process)d - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S%z"
            )
            logging.info("A log config could not be found - running with a basic config")

        if settings.log_override_path.is_file():
            configuration: dict[str, str] = json.loads(settings.log_override_path.read_text())

            for log_name, log_level in configuration.items():
                logging.getLogger(name=log_name).setLevel(level=logging.getLevelName(level=log_level))


def get_logger(source: str | pathlib.Path | type | object) -> logging.Logger:
    setup_logging()

    if isinstance(source, type) and not isinstance(source, (str, pathlib.Path)):
        source = source.__module__
    elif isinstance(source, str):
        possible_path: pathlib.Path = pathlib.Path(source)
        if possible_path.absolute().is_relative_to(settings.root):
            source = possible_path

    if isinstance(source, pathlib.Path):
        if source.absolute().is_relative_to(settings.root):
            name_parts: list[str] = [*source.absolute().parts[len(settings.root.parts):-1], source.stem]
            source = ".".join(name_parts)

    if not isinstance(source, str):
        source = source.__class__.__module__

    return logging.getLogger(source)


