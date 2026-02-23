"""
System wide settings for runtime configuration
"""
import collections.abc as generic
import enum
import os
import pathlib
import typing
from threading import RLock

_SOURCE_PATH: pathlib.Path = pathlib.Path(__file__)

APP_PREFIX: typing.Final[str] = "HERBIE_NG"
MISSING: object = object()


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
    TEMPLATE_DIRECTORY = f"{APP_PREFIX}_TEMPLATE_DIRECTORY"
    DEFAULT_MODEL = f"{APP_PREFIX}_DEFAULT_MODEL"
    SAVE_DIRECTORY = f"{APP_PREFIX}_SAVE_DIRECTORY"
    TOML_CONFIGURATION_PATH = f"{APP_PREFIX}_TOML_CONFIG_PATH"


def _find_root_directory() -> pathlib.Path:
    directory: pathlib.Path | str | None = os.environ.get(EnvironmentKey.ROOT_DIRECTORY)

    if not directory:
        library_name: str = EnvironmentKey.__module__.split(".")[0]

        directory: pathlib.Path = _SOURCE_PATH
        while directory.name != library_name:
            directory = directory.parent

    if isinstance(directory, str):
        directory = pathlib.Path(directory)

    return directory


_DEFAULT_SETTINGS: generic.Mapping[EnvironmentKey, typing.Any | generic.Callable[[], typing.Any]] = {
    EnvironmentKey.APPLICATION_NAME: "HerbieNG",
    EnvironmentKey.TOML_CONFIGURATION_PATH: lambda: pathlib.Path.home() / ".config" / f"{_DEFAULT_SETTINGS[EnvironmentKey.APPLICATION_NAME]}.toml",
    EnvironmentKey.ROOT_DIRECTORY: _find_root_directory(),
    EnvironmentKey.RESOURCE_DIRECTORY: lambda: _DEFAULT_SETTINGS[EnvironmentKey.ROOT_DIRECTORY] / "resources",
    EnvironmentKey.CONFIGURATION_DIRECTORY: lambda: _DEFAULT_SETTINGS[EnvironmentKey.RESOURCE_DIRECTORY] / "config",
    EnvironmentKey.TEMPLATE_DIRECTORY: lambda: _DEFAULT_SETTINGS[EnvironmentKey.RESOURCE_DIRECTORY] / "templates"
}


def _get_application_default(key: EnvironmentKey, default=None) -> typing.Optional[typing.Any]:
    value = _DEFAULT_SETTINGS.get(key, default)
    if isinstance(value, generic.Callable):
        value = value()
    return value


def load_config_toml() -> generic.Mapping[str, typing.Any]:
    configuration_path: pathlib.Path = pathlib.Path(
        os.environ.get(EnvironmentKey.TOML_CONFIGURATION_PATH, pathlib.Path.home() / ".config" / "HerbieNG.toml")
    )


class _Settings(generic.Mapping):
    def __len__(self):
        with self.__settings_lock:
            return len(self.__values)

    def __iter__(self):
        with self.__settings_lock:
            current_keys: generic.Sequence[str] = list(self.__values.keys())
            return iter(current_keys)

    def __contains__(self, item):
        with self.__settings_lock:
            return item in self.__values

    def __init__(self, **kwargs):
        self.__settings_lock: RLock = RLock()
        self.__values: dict[str, typing.Any] = {
            **os.environ,
            **kwargs
        }

    def __getitem__(self, item):
        with self.__settings_lock:
            return self.__values[item]

    def get(self, key: str, default=MISSING) -> typing.Any:
        with self.__settings_lock:
            if key in self.__values:
                return self.__values.get(key)

            if default == MISSING and key in EnvironmentKey:
                default = _get_application_default(EnvironmentKey(key))
            elif default == MISSING:
                default = None
            return self.__values.setdefault(key, default)

    @property
    def root(self) -> pathlib.Path:
        with self.__settings_lock:
            return pathlib.Path(self.get(EnvironmentKey.ROOT_DIRECTORY))

    def __get_directory(self, key: str, *, default: pathlib.Path = MISSING) -> pathlib.Path:
        with self.__settings_lock:
            directory: pathlib.Path | str | None = self.get(key, default=default)

            if not directory:
                directory = default
                self.__values[key] = directory

            if isinstance(directory, str):
                directory = pathlib.Path(directory)
                self.__values[key] = directory

            return directory

    @property
    def resource_directory(self) -> pathlib.Path:
        return self.__get_directory(
            EnvironmentKey.RESOURCE_DIRECTORY
        )

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
        return _is_true(self.__values.setdefault(EnvironmentKey.DEBUG, False))

    @property
    def application_name(self) -> str:
        with self.__settings_lock:
            return self.__values.setdefault(
                EnvironmentKey.APPLICATION_NAME,
                _DEFAULT_SETTINGS.get(EnvironmentKey.APPLICATION_NAME)
            )

    @property
    def pando_url(self) -> str:
        return self.__values.setdefault(EnvironmentKey.PANDO_URL, "https://pando-rgw01.chpc.utah.edu/")


settings: typing.Final[_Settings] = _Settings()
