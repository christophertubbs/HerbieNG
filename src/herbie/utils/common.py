"""
Common functions that may be reused just about anywhere

WARNING: Keep as few references to this project within this file as possible in order to avoid circular dependencies
"""
import inspect
import pathlib
import re
import typing
from datetime import timedelta

T = typing.TypeVar("T")
ISO_8601_DURATION_PATTERN: typing.Final[re.Pattern] = re.compile(
    r"P((?P<days>\d+)D)?(T((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+(\.\d*)?)S)?)?"
)


def expand_path(
    input_path: pathlib.Path | str,
    *,
    resolve: bool = False,
    absolute: bool = False,
) -> pathlib.Path:
    """
    Expand a path by resolving all relative pathing and evaluating references to environment variables

    :param input_path: The path to expand
    :param resolve: Whether to evaluate all symbolic links
    :param absolute: Whether to convert the path to absolute terms
    :returns: The fully evaluated path
    """
    import os
    path_object: pathlib.Path = pathlib.Path(os.path.expandvars(str(input_path))).expanduser()

    if resolve:
        path_object = path_object.resolve()

    if absolute:
        path_object = path_object.absolute()

    return path_object


def get_all_implementations(parent_class: type[T], encountered_types: list[type[T]] | None = None) -> list[type[T]]:
    """
    Get all implementations of a given class and its children

    WARNING: Only classes that have been imported are considered. If a candidate is in another module that has not
    been imported, that candidate will NOT be included.

    :param parent_class: The class whose implementations to find
    :param encountered_types: The types that have already been encountered
    :returns: All concrete implmentations of 'parent_class'
    """
    if not isinstance(parent_class, type):
        parent_class = parent_class.__class__

    if encountered_types is None:
        encountered_types = []

    if parent_class in encountered_types:
        return []

    implementations: list[type[T]] = []
    if not inspect.isabstract(parent_class) and parent_class not in encountered_types:
        implementations.append(parent_class)

    encountered_types.append(parent_class)

    for subclass in parent_class.__subclasses__():
        if subclass in encountered_types:
            continue

        implementations_of_subclass: list[type[T]] = get_all_implementations(
            parent_class=subclass,
            encountered_types=encountered_types
        )

        implementations.extend([
            implementation
            for implementation in implementations_of_subclass
            if implementation not in implementations
        ])

    return implementations


def parse_ISO_8601_duration(duration: str) -> timedelta:
    duration: str = duration.strip().upper()

    matched_8601_pattern: re.Match | None = ISO_8601_DURATION_PATTERN.search(duration)

    if matched_8601_pattern is None:
        raise ValueError(
            f"Cannot parse '{duration}' as an ISO 8601 duration - it does not fit the specified pattern of 'P#DT#H#M#S'"
        )

    duration_parts: dict[str, float] = {
        key: float(value)
        for key, value in matched_8601_pattern.groupdict().items()
        if value is not None
    }

    return timedelta(**duration_parts)


def timedelta_to_ISO_8601_duration(delta: timedelta) -> str:
    """
    Convert a vanilla timedelta into an ISO8601 duration string supporting days, hours. minutes, and seconds.

    A missing delta or a duration of 0 results in 'PT0S', indicating no seconds

    :param delta: The timedelta to convert
    :returns: The timedelta in a representation that matches the ISO8601 Duration Specification, without support for years or months.
    """
    if delta is None or isinstance(delta, timedelta) and delta.total_seconds() == 0.0:
        return "PT0S"

    if not isinstance(delta, timedelta):
        raise TypeError(
            f"Cannot convert {delta} (type={type(delta)}) to ISO 8601 - convert it to a vanilla timedelta first"
        )

    iso_parts: list[str] = [
        "P"
    ]

    if delta < timedelta(microseconds=0):
        iso_parts.insert(0, '-')

    seconds: int = int(delta.total_seconds())

    if seconds < 0:
        iso_parts.insert(0, '-')
        seconds = abs(seconds)

    days, seconds = divmod(seconds, 60 * 60 * 24)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)

    if days:
        iso_parts.append(f"{days}D")

    if hours or minutes or seconds:
        iso_parts.append("T")

        if hours:
            iso_parts.append(f"{hours}H")

        if minutes:
            iso_parts.append(f"{minutes}M")

        if seconds:
            iso_parts.append(f"{seconds}S")

    return "".join(iso_parts)
