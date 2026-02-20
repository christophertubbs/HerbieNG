"""
Defines the Template provider for CFS
"""
__all__ = ["CFSTemplateProvider"]

import collections.abc as generic

from herbie.models.templates.base import BaseTemplate
from herbie.models.templates.base import TemplateProvider


class CFSTemplateProvider(TemplateProvider):
    MODEL_FAMILY = "CFS"

    @classmethod
    def get_templates(cls) -> generic.Sequence[BaseTemplate]:
        templates: list[BaseTemplate] = []

        templates.append(
            BaseTemplate(
                name="CFS",
                description="NOAA Climate Forecast System",
                product="time_series",
                details={

                },
                sources={

                },
                idx_suffix=[],
                path="",
                localfile=""
            )
        )

        return templates
