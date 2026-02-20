"""
System wide settings for runtime configuration
"""
import enum
import os
import pathlib
import typing

_SOURCE_PATH: pathlib.Path = pathlib.Path(__file__)

APP_PREFIX: typing.Final[str] = "HERBIE_NG"


def _is_true(value) -> bool:
    return str(value) in ('t', 'true', 'y', 'yes', '1', 'on')


def _is_false(value) -> bool:
    return str(value) in ('f', 'false', 'n', 'no', '0', 'off')


class EnvironmentKey(enum.StrEnum):
    ROOT_DIRECTORY = f"{APP_PREFIX}_ROOT"
    """The environment variable for where the root of this library should be considered"""
    DEBUG = f"{APP_PREFIX}_DEBUG"
    CONFIGURATION_DIRECTORY = f"{APP_PREFIX}_CONFIG_PATH"
    APPLICATION_NAME = f"{APP_PREFIX}_APPLICATION_NAME"
    RESOURCE_DIRECTORY = f"{APP_PREFIX}_RESOURCE_PATH"
    LOG_OVERRIDE_PATH = f"{APP_PREFIX}_LOG_OVERRIDE_PATH"
    LOG_CONFIG_PATH = f"{APP_PREFIX}_LOG_CONFIG_PATH"
    PANDO_URL = f"{APP_PREFIX}_PANDO_URL"


class _Settings:
    def __init__(self, **kwargs):
        self.__values: dict[str, typing.Any] = {
            **os.environ,
            **kwargs
        }

    def __getitem__(self, item):
        return self.__values[item]

    def get(self, key: str, default = None):
        return self.__values.get(key, default)

    @property
    def root(self) -> pathlib.Path:
        directory: pathlib.Path | str | None = self.get(EnvironmentKey.ROOT_DIRECTORY)
        if not directory:
            library_name: str = self.__class__.__module__.split(".")[0]
            directory: pathlib.Path = _SOURCE_PATH
            while directory.name != library_name:
                directory = directory.parent

            self.__values[EnvironmentKey.ROOT_DIRECTORY] = directory

        if isinstance(directory, str):
            directory = pathlib.Path(directory)
            self.__values[EnvironmentKey.ROOT_DIRECTORY] = directory

        return directory

    def __get_directory(self, key: str, *, default: pathlib.Path) -> pathlib.Path:
        directory: pathlib.Path | str | None = self.get(key)

        if not directory:
            directory = default
            self.__values[key] = directory

        if isinstance(directory, str):
            directory = pathlib.Path(directory)
            self.__values[key] = directory

        return directory

    @property
    def resource_directory(self) -> pathlib.Path:
        directory: pathlib.Path = self.__get_directory(
            EnvironmentKey.RESOURCE_DIRECTORY,
            default=self.root / "resources"
        )
        return directory

    @property
    def configuration_path(self) -> pathlib.Path:
        directory: pathlib.Path = self.__get_directory(
            EnvironmentKey.CONFIGURATION_DIRECTORY,
            default=self.resource_directory / "config"
        )
        return directory

    @property
    def log_config_path(self) -> pathlib.Path:
        directory: pathlib.Path = self.__get_directory(
            EnvironmentKey.LOG_CONFIG_PATH,
            default=self.configuration_path / "default.log_config.json"
        )
        return directory

    @property
    def log_override_path(self) -> pathlib.Path:
        directory: pathlib.Path = self.__get_directory(
            EnvironmentKey.LOG_OVERRIDE_PATH,
            default=self.configuration_path / "default.log_override.json"
        )
        return directory

    @property
    def debug(self) -> bool:
        return _is_true(self.__values.get(EnvironmentKey.DEBUG, False))

    @property
    def application_name(self) -> str:
        name: str | None = self.__values.get(EnvironmentKey.APPLICATION_NAME)

        if not name:
            name = "HerbieNG"
            self.__values[EnvironmentKey.APPLICATION_NAME] = name

        return name

    @property
    def pando_url(self) -> str:
        return self.__values.setdefault(EnvironmentKey.PANDO_URL, "https://pando-rgw01.chpc.utah.edu/")


settings: typing.Final[_Settings] = _Settings()
