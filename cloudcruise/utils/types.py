from __future__ import annotations

from dataclasses import fields, is_dataclass
from types import UnionType
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints


T = TypeVar("T")


def to_dataclass(data: Any, cls: type[T]) -> T:
    """Build a dataclass instance from API JSON.

    Unknown fields are ignored so new backend response fields do not break
    older SDK versions. Known nested dataclass fields are converted
    recursively.
    """
    if isinstance(data, cls):
        return data
    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass type")
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict to build {cls.__name__}, got {type(data).__name__}")

    hints = get_type_hints(cls)
    kwargs = {}
    for field in fields(cls):
        if field.name not in data:
            continue
        kwargs[field.name] = _coerce_value(data[field.name], hints.get(field.name, field.type))
    return cls(**kwargs)


def _coerce_value(value: Any, annotation: Any) -> Any:
    if value is None or annotation is Any:
        return value

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (Union, UnionType):
        for option in args:
            if option is type(None):
                continue
            try:
                return _coerce_value(value, option)
            except (TypeError, ValueError):
                continue
        return value

    if origin is list:
        item_type = args[0] if args else Any
        if not isinstance(value, list):
            return value
        return [_coerce_value(item, item_type) for item in value]

    if origin is dict:
        value_type = args[1] if len(args) == 2 else Any
        if not isinstance(value, dict) or value_type is Any:
            return value
        return {k: _coerce_value(v, value_type) for k, v in value.items()}

    if isinstance(annotation, type) and is_dataclass(annotation):
        return to_dataclass(value, annotation)

    return value
