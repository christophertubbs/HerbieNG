"""
Definitions for lazy objects
"""
import collections.abc as generic
import typing
from functools import partial
from threading import RLock

KT = typing.TypeVar("KT")
T = typing.TypeVar("T")
ParamSpec = typing.ParamSpec("ParamSpec")


_MISSING: object = object()


class LazyValue(typing.Generic[T]):
    def __init__(self, factory_function: generic.Callable[ParamSpec, T] | partial[T], *args, **kwargs):
        if isinstance(factory_function, partial) and args:
            raise RuntimeError(
                f"Cannot create a LazyValue whose factory is partial and has positional arguments. "
                f"Only keyword arguments are allowable for partials"
            )
        self.__factory_function: generic.Callable[ParamSpec, T] | partial = factory_function
        self.__args = args
        self.__kwargs = kwargs

    def get(self) -> T:
        if isinstance(self.__factory_function, partial):
            return self.__factory_function(**self.__kwargs)
        return self.__factory_function(*self.__args, **self.__kwargs)

    def __get__(self, instance: object | None, owner: type | None = None) -> T:
        return self.get()


class LazyDictValuesView(generic.ValuesView[T], typing.Generic[KT, T]):
    def __init__(self, mapping: generic.Mapping[KT, T]):
        self.__mapping = mapping

    def __len__(self):
        return len(self.__mapping)

    def __contains__(self, item: KT):
        for key in self.__mapping:
            if self.__mapping[key] == item:
                return True
        return False

    def __iter__(self):
        keys: list[KT] = list(self.__mapping.keys())
        for key in keys:
            yield self.__mapping[key]


class LazyDictItemsView(generic.ItemsView[KT, T], typing.Generic[KT, T]):
    def __init__(self, mapping: generic.Mapping[KT, T]):
        self.__mapping = mapping

    def __len__(self):
        return len(self.__mapping)

    def __iter__(self):
        keys: list[KT] = list(self.__mapping.keys())
        for key in keys:
            yield key, self.__mapping[key]

    def __contains__(self, pair: tuple[KT, T]) -> bool:
        if not isinstance(pair, tuple) or len(pair) != 2:
            return False

        key: KT = pair[0]
        value: T = pair[1]

        if key in self.__mapping:
            return self.__mapping[key] == value

        return False


class LazyDict(generic.MutableMapping[KT, T]):
    def __init__(self, values: generic.Mapping[KT, T] | None):
        self.__internal_values: dict[KT, T] = {}
        self.__factories: dict[KT, LazyValue[T]] = {}
        self.__lock: RLock = RLock()

        if values is None:
            values = {}

        for key in values:
            value: T = values[key]
            if isinstance(value, partial):
                self.__factories[key] = LazyValue(value)
                self.__internal_values[key] = _MISSING
            elif isinstance(value, LazyValue):
                self.__factories[key] = value
                self.__internal_values[key] = _MISSING
            else:
                self.__internal_values[key] = value

    def __setitem__(self, key, value, /):
        with self.__lock:
            if isinstance(value, partial):
                self.__factories[key] = LazyValue(value)
                self.__internal_values[key] = _MISSING
            elif isinstance(value, LazyValue):
                self.__factories[key] = value
                self.__internal_values[key] = _MISSING
            else:
                self.__internal_values[key] = value
                if key in self.__factories:
                    del self.__factories[key]

    def __delitem__(self, key, /):
        with self.__lock:
            if key not in self.__internal_values:
                raise KeyError(f"'{key}' is not a valid key")
            del self.__internal_values[key]
            if key in self.__factories:
                del self.__factories[key]

    def __getitem__(self, key, /):
        with self.__lock:
            if key not in self.__internal_values:
                raise KeyError(f"No value keyed by '{key}' could be found")

            if self.__internal_values[key] == _MISSING:
                value: T = self.__factories[key].get()
                self.__internal_values[key] = value
                return value
            return self.__internal_values[key]

    def __len__(self):
        return len(self.__internal_values)

    def __iter__(self):
        return iter(self.__internal_values)

    def set_lazy_value(self, key: KT, function: generic.Callable[ParamSpec, T] | partial[T], *args, **kwargs):
        with self.__lock:
            if not isinstance(function, (generic.Callable, partial)):
                raise TypeError(
                    f"A function or partial must be given in order to create a lazy value - "
                    f"instead received '{function}' (type={type(function)})"
                )
            self.__internal_values[key] = _MISSING
            self.__factories[key] = LazyValue(factory_function=function, *args, **kwargs)

    def get(self, key, /, default=None) -> T | None:
        with self.__lock:
            if key not in self.__internal_values:
                return default
            return self[key]

    def materialize(self) -> typing.Self:
        with self.__lock:
            for key, lazy_value in self.__factories.items():
                if self.__internal_values[key] == _MISSING:
                    self.__internal_values[key] = lazy_value.get()
        return self

    def keys(self) -> generic.KeysView[KT]:
        with self.__lock:
            return self.__internal_values.keys()

    def values(self) -> generic.ValuesView[T]:
        return LazyDictValuesView(self)

    def items(self) -> generic.ItemsView[KT, T]:
        return LazyDictItemsView(self)

    def setdefault(self, key, default=None, /):
        with self.__lock:
            if key in self.__internal_values:
                return self[key]
            self.__internal_values[key] = default
            return default

    def pop(self, key, /) -> T:
        with self.__lock:
            if key not in self.keys():
                raise KeyError(f"No value keyed by '{key}' could be found")
            value = self[key]
            del self.__internal_values[key]
            if key in self.__factories:
                del self.__factories[key]
            return value

    def popitem(self) -> tuple[KT, T]:
        with self.__lock:
            key: KT = next(reversed(self.__internal_values))
            value: T = self.pop(key)
            return key, value

    def rematerialize(self, key: KT) -> T:
        with self.__lock:
            if key not in self.__factories:
                raise KeyError(f"There is not a factory function for the key '{key}' (type={type(key)})")
            new_value: T = self.__factories[key].get()
            old_value = self.__internal_values[key]
            self.__internal_values[key] = new_value
            del old_value
            return new_value

    def unload(self) -> typing.Self:
        with self.__lock:
            for key in self.__factories.keys():
                old_value = self.__internal_values[key]
                self.__internal_values[key] = _MISSING
                del old_value
        return self
