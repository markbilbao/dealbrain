"""Dataclass JSON codec for operational persistence (Sprint 23).

Round-trips frozen dataclasses, enums, datetimes, tuples, and nested structures
without embedding domain decision logic in adapters.
"""

from __future__ import annotations

import types
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints


def encode(value: Any) -> Any:
    """Convert a domain value into JSON-compatible data."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"__type__": "date", "value": value.isoformat()}
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return {
            "__type__": "tuple" if isinstance(value, tuple) else "list",
            "items": [encode(item) for item in value],
        }
    if isinstance(value, frozenset):
        return {"__type__": "frozenset", "items": [encode(item) for item in value]}
    if isinstance(value, set):
        return {"__type__": "set", "items": [encode(item) for item in value]}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__type__": "dataclass",
            "qualname": f"{value.__class__.__module__}.{value.__class__.__qualname__}",
            "fields": {f.name: encode(getattr(value, f.name)) for f in fields(value)},
        }
    raise TypeError(f"Cannot encode persistence value of type {type(value)!r}")


def decode(annotation: Any, raw: Any) -> Any:
    """Reconstruct a typed value from encoded JSON data."""
    if raw is None:
        return None

    origin = get_origin(annotation)
    if origin is None and isinstance(annotation, type) and is_dataclass(annotation):
        return _decode_dataclass(annotation, raw)

    if isinstance(raw, dict) and raw.get("__type__") == "dataclass":
        cls = _resolve_qualname(str(raw["qualname"]))
        return _decode_dataclass(cls, raw)

    if origin is Union or origin is types.UnionType:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if raw is None:
            return None
        last_error: Exception | None = None
        for arg in args:
            try:
                return decode(arg, raw)
            except Exception as exc:  # noqa: BLE001 — try next union member
                last_error = exc
        if last_error is not None:
            raise last_error
        return raw

    if origin in (list, tuple, set, frozenset):
        item_type = get_args(annotation)[0] if get_args(annotation) else Any
        items_raw = raw["items"] if isinstance(raw, dict) and "items" in raw else raw
        items = [decode(item_type, item) for item in items_raw]
        if origin is list or (isinstance(raw, dict) and raw.get("__type__") == "list"):
            return list(items)
        if origin is frozenset or (isinstance(raw, dict) and raw.get("__type__") == "frozenset"):
            return frozenset(items)
        if origin is set or (isinstance(raw, dict) and raw.get("__type__") == "set"):
            return set(items)
        return tuple(items)

    if origin is dict:
        key_type, val_type = get_args(annotation) or (str, Any)
        assert isinstance(raw, dict)
        return {decode(key_type, k): decode(val_type, v) for k, v in raw.items() if k != "__type__"}

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(raw)

    if annotation is datetime or (
        isinstance(raw, dict) and raw.get("__type__") == "datetime"
    ):
        text = raw["value"] if isinstance(raw, dict) else raw
        return datetime.fromisoformat(str(text))

    if annotation is date or (isinstance(raw, dict) and raw.get("__type__") == "date"):
        text = raw["value"] if isinstance(raw, dict) else raw
        return date.fromisoformat(str(text))

    if annotation is Any or annotation is object:
        if isinstance(raw, dict) and "__type__" in raw:
            kind = raw["__type__"]
            if kind == "datetime":
                return datetime.fromisoformat(str(raw["value"]))
            if kind == "date":
                return date.fromisoformat(str(raw["value"]))
            if kind in {"list", "tuple", "set", "frozenset"}:
                items = [decode(Any, item) for item in raw["items"]]
                if kind == "tuple":
                    return tuple(items)
                if kind == "set":
                    return set(items)
                if kind == "frozenset":
                    return frozenset(items)
                return list(items)
            if kind == "dataclass":
                cls = _resolve_qualname(str(raw["qualname"]))
                return _decode_dataclass(cls, raw)
        return raw

    return raw


def encode_entity(entity: Any) -> dict[str, Any]:
    """Encode a dataclass entity to a JSON object."""
    encoded = encode(entity)
    if not isinstance(encoded, dict):
        raise TypeError("Entity encoding must produce an object")
    return encoded


def decode_entity(cls: type[Any], payload: dict[str, Any]) -> Any:
    """Decode a JSON object into a dataclass entity of ``cls``."""
    return decode(cls, payload)


def _decode_dataclass(cls: type[Any], raw: Any) -> Any:
    if is_dataclass(raw) and isinstance(raw, cls):
        return raw
    if not isinstance(raw, dict):
        raise TypeError(f"Expected dict payload for {cls.__name__}, got {type(raw)!r}")
    field_data = raw["fields"] if raw.get("__type__") == "dataclass" else raw
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.name not in field_data:
            continue
        annotation = hints.get(f.name, Any)
        kwargs[f.name] = decode(annotation, field_data[f.name])
    return cls(**kwargs)


def _resolve_qualname(qualname: str) -> type[Any]:
    module_name, _, cls_name = qualname.rpartition(".")
    if not module_name:
        raise TypeError(f"Invalid dataclass qualname: {qualname}")
    import importlib

    module = importlib.import_module(module_name)
    # Support nested classes via qualname segments.
    obj: Any = module
    for part in cls_name.split("."):
        obj = getattr(obj, part)
    if not isinstance(obj, type):
        raise TypeError(f"Resolved object is not a type: {qualname}")
    return obj
