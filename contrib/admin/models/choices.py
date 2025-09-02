# -*- coding: utf-8 -*-
"""
choices

Django-like Choices for Tortoise/Pydantic v2.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from enum import Enum, IntEnum
from typing import Any, Iterable, List, Tuple, cast


class ChoicesMixin:
    """Common helpers for choices-like enums."""

    label: str  # set on each member

    @classmethod
    def choices(cls) -> List[Tuple[Any, str]]:
        members = cast(Iterable[Any], cls)
        return [(m.value, m.label) for m in members]  # type: ignore[attr-defined]

    @classmethod
    def values(cls) -> List[Any]:
        members = cast(Iterable[Any], cls)
        return [m.value for m in members]

    @classmethod
    def labels(cls) -> List[str]:
        members = cast(Iterable[Any], cls)
        return [m.label for m in members]  # type: ignore[attr-defined]

    @classmethod
    def get_label(cls, value: Any) -> str | None:
        for m in cast(Iterable[Any], cls):  # type: ignore[assignment]
            if m.value == value:
                return getattr(m, "label", str(m))
        return None

    @classmethod
    def from_value(cls, value: Any) -> ChoicesMixin:
        for m in cast(Iterable[Any], cls):  # type: ignore[assignment]
            if getattr(m, "value", None) == value:
                return cast(ChoicesMixin, m)
        raise ValueError(f"{cls.__name__}: no member with value {value!r}")


class StrChoices(ChoicesMixin, str, Enum):
    """String-based choices: members defined as ('value', 'Label')."""

    def __new__(cls, value: str, label: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label  # type: ignore[attr-defined]
        return obj

    def __str__(self) -> str:
        return str(self.value)


class IntChoices(ChoicesMixin, IntEnum):
    """Integer-based choices: members defined as (value, 'Label')."""

    def __new__(cls, value: int, label: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label  # type: ignore[attr-defined]
        return obj

    def __str__(self) -> str:
        return str(self.value)

# The End

