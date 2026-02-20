"""
Base model definitions for import model specifications
"""
import abc
import collections.abc as generic
import typing

import pydantic


class BaseTemplate(pydantic.BaseModel):
    name: str
    description: str
    details: dict[str, str]
    path: str
    product: str
    sources: dict[str, str]
    idx_suffix: list[str]
    localfile: str | generic.Callable[[dict], str]
    validator: typing.Optional[str | generic.Callable[["BaseTemplate"], typing.Any]] = pydantic.Field(default=None)


class TemplateProvider(abc.ABC):
    """
    Provides specialized access to model templates
    """
    REQUIRED_FIELDS = ['MODEL_FAMILY']

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls is TemplateProvider:
            return

        missing_fields: list[str] = [
            field
            for field in cls.REQUIRED_FIELDS
            if not hasattr(cls, field)
        ]

        if missing_fields:
            raise TypeError(
                f"Incorrect definition of '{cls.__qualname__}' - "
                f"the following fields have not been defined: {', '.join(missing_fields)}"
            )

    @classmethod
    @abc.abstractmethod
    def get_templates(cls) -> generic.Sequence[BaseTemplate]:
        ...
