from __future__ import annotations

from typing import Any, get_args, get_origin, get_type_hints


class _MissingType:
    pass


MISSING = _MissingType()


class FieldInfo:
    def __init__(self, default: Any = MISSING, default_factory=None):
        self.default = default
        self.default_factory = default_factory


def Field(default: Any = MISSING, default_factory=None):
    return FieldInfo(default=default, default_factory=default_factory)


def _is_basemodel_type(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, BaseModel)


def _coerce_value(annotation: Any, value: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (list, tuple) and args:
        return [_coerce_value(args[0], item) for item in value]

    if origin is set and args:
        return {_coerce_value(args[0], item) for item in value}

    if origin is dict and len(args) == 2:
        key_type, value_type = args
        return {
            _coerce_value(key_type, key): _coerce_value(value_type, item)
            for key, item in value.items()
        }

    if origin is None and _is_basemodel_type(annotation) and isinstance(value, dict):
        return annotation(**value)

    return value


class BaseModel:
    def __init__(self, **data: Any) -> None:
        hints = get_type_hints(self.__class__)

        for field_name, annotation in hints.items():
            if field_name in data:
                value = data[field_name]
            else:
                default = getattr(self.__class__, field_name, MISSING)
                if isinstance(default, FieldInfo):
                    if default.default_factory is not None:
                        value = default.default_factory()
                    elif default.default is not MISSING:
                        value = default.default
                    else:
                        value = None
                elif default is not MISSING:
                    value = default
                else:
                    value = None

            setattr(self, field_name, _coerce_value(annotation, value))

    def model_dump(self) -> dict[str, Any]:
        hints = get_type_hints(self.__class__)
        result = {}
        for field_name in hints:
            value = getattr(self, field_name)
            if isinstance(value, BaseModel):
                result[field_name] = value.model_dump()
            elif isinstance(value, list):
                result[field_name] = [item.model_dump() if isinstance(item, BaseModel) else item for item in value]
            elif isinstance(value, dict):
                result[field_name] = {
                    key: item.model_dump() if isinstance(item, BaseModel) else item for key, item in value.items()
                }
            elif isinstance(value, set):
                result[field_name] = set(value)
            else:
                result[field_name] = value
        return result
