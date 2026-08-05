from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from jsonschema import Draft7Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import (  # type: ignore[import-untyped]
    SchemaError,
    ValidationError,
)

from .types import (
    InputValidationError,
    InvalidTypeDetail,
    SchemaErrorDetail,
)


_SINGLE_SCHEMA_KEYWORDS = {
    "additionalItems",
    "additionalProperties",
    "contains",
    "else",
    "if",
    "not",
    "propertyNames",
    "then",
}
_ARRAY_SCHEMA_KEYWORDS = {"allOf", "anyOf", "oneOf"}
_MAPPING_SCHEMA_KEYWORDS = {
    "definitions",
    "patternProperties",
    "properties",
}


def validate_input_schema(schema: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    external_ref = _first_external_ref(schema)
    if external_ref is not None:
        detail = SchemaErrorDetail(
            instancePath="",
            schemaPath=external_ref[0],
            keyword="$ref",
            message=f"external reference is not allowed: {external_ref[1]}",
        )
        raise InputValidationError(
            f"Workflow input schema is invalid: {detail.message}",
            schema_errors=[detail],
        )

    try:
        Draft7Validator.check_schema(schema)
    except SchemaError as exc:
        detail = SchemaErrorDetail(
            instancePath="",
            schemaPath=_json_pointer(exc.absolute_path, prefix="#"),
            keyword="schema",
            message=exc.message,
        )
        raise InputValidationError(
            f"Workflow input schema is invalid: {exc.message}",
            schema_errors=[detail],
        ) from exc

    errors = sorted(
        Draft7Validator(schema).iter_errors(payload),
        key=lambda error: (
            _json_pointer(error.absolute_path),
            _json_pointer(error.absolute_schema_path, prefix="#"),
            str(error.validator),
            error.message,
        ),
    )
    if not errors:
        return

    schema_errors = [_to_schema_error(error) for error in errors]
    missing_required = _missing_required(errors)
    invalid_types = _invalid_types(errors)
    unknown_keys = _unknown_keys(errors)
    message = _validation_message(
        schema_errors,
        missing_required,
        invalid_types,
        unknown_keys,
    )
    raise InputValidationError(
        message,
        missing_required,
        invalid_types,
        unknown_keys,
        schema_errors,
    )


def input_validation_error_from_response(
    response: Mapping[str, Any],
    request_body: Any = None,
) -> InputValidationError | None:
    raw_errors = response.get("run_input_variables_errors")
    if not isinstance(raw_errors, list):
        return None

    schema = response.get("input_schema")
    if not isinstance(schema, Mapping):
        schema = {}
    payload: Mapping[str, Any] = {}
    if isinstance(request_body, Mapping):
        request_payload = request_body.get("run_input_variables")
        if isinstance(request_payload, Mapping):
            payload = request_payload

    schema_errors: list[SchemaErrorDetail] = []
    missing_required: list[str] = []
    invalid_types: list[InvalidTypeDetail] = []
    unknown_keys: list[str] = []

    for raw_error in raw_errors:
        if not isinstance(raw_error, Mapping):
            continue
        field = str(raw_error.get("field") or "")
        keyword = str(raw_error.get("keyword") or "validation")
        error_message = str(raw_error.get("message") or "Invalid value")
        expected = raw_error.get("expected")
        if not isinstance(expected, Mapping):
            expected = {}

        instance_path = field if field.startswith("/") else ""
        schema_path = (
            field
            if field.startswith("#")
            else _schema_path_for_instance(schema, instance_path, keyword)
        )
        schema_errors.append(
            SchemaErrorDetail(
                instancePath=instance_path,
                schemaPath=schema_path,
                keyword=keyword,
                message=error_message,
            )
        )

        if keyword == "required":
            missing_property = expected.get("missingProperty")
            if isinstance(missing_property, str):
                missing_field = (
                    f"{instance_path}/{_escape_pointer(missing_property)}"
                    if instance_path
                    else missing_property
                )
                if missing_field not in missing_required:
                    missing_required.append(missing_field)
        elif keyword == "type":
            expected_type = expected.get("type")
            expected_types = (
                [str(item) for item in expected_type]
                if isinstance(expected_type, list)
                else str(expected_type or "any").split(",")
            )
            invalid_types.append(
                InvalidTypeDetail(
                    field=_display_field(instance_path),
                    expected_display=" | ".join(expected_types),
                    actual=_detect_type(_value_at_pointer(payload, instance_path)),
                )
            )
        elif keyword == "additionalProperties":
            additional_property = expected.get("additionalProperty")
            if isinstance(additional_property, str):
                unknown_field = (
                    f"{instance_path}/{_escape_pointer(additional_property)}"
                    if instance_path
                    else additional_property
                )
                if unknown_field not in unknown_keys:
                    unknown_keys.append(unknown_field)

    if not schema_errors:
        detail_message = str(
            response.get("message") or "Validation failed for run_input_variables"
        )
        schema_errors.append(
            SchemaErrorDetail(
                instancePath="",
                schemaPath="",
                keyword="validation",
                message=detail_message,
            )
        )

    message = _validation_message(
        schema_errors,
        missing_required,
        invalid_types,
        unknown_keys,
    )
    return InputValidationError(
        message,
        missing_required,
        invalid_types,
        unknown_keys,
        schema_errors,
    )


def _first_external_ref(
    schema: Any,
    path: tuple[str | int, ...] = (),
) -> tuple[str, str] | None:
    if not isinstance(schema, Mapping):
        return None

    ref = schema.get("$ref")
    if isinstance(ref, str) and not ref.startswith("#"):
        return _json_pointer((*path, "$ref"), prefix="#"), ref

    for keyword in _SINGLE_SCHEMA_KEYWORDS:
        child = schema.get(keyword)
        if isinstance(child, Mapping):
            found = _first_external_ref(child, (*path, keyword))
            if found:
                return found

    items = schema.get("items")
    if isinstance(items, Mapping):
        found = _first_external_ref(items, (*path, "items"))
        if found:
            return found
    elif isinstance(items, Sequence) and not isinstance(items, (str, bytes)):
        for index, child in enumerate(items):
            found = _first_external_ref(child, (*path, "items", index))
            if found:
                return found

    for keyword in _ARRAY_SCHEMA_KEYWORDS:
        children = schema.get(keyword)
        if isinstance(children, Sequence) and not isinstance(children, (str, bytes)):
            for index, child in enumerate(children):
                found = _first_external_ref(child, (*path, keyword, index))
                if found:
                    return found

    for keyword in _MAPPING_SCHEMA_KEYWORDS:
        children = schema.get(keyword)
        if isinstance(children, Mapping):
            for name, child in children.items():
                found = _first_external_ref(child, (*path, keyword, str(name)))
                if found:
                    return found

    dependencies = schema.get("dependencies")
    if isinstance(dependencies, Mapping):
        for name, child in dependencies.items():
            if isinstance(child, Mapping):
                found = _first_external_ref(
                    child,
                    (*path, "dependencies", str(name)),
                )
                if found:
                    return found

    return None


def _to_schema_error(error: ValidationError) -> SchemaErrorDetail:
    return SchemaErrorDetail(
        instancePath=_json_pointer(error.absolute_path),
        schemaPath=_json_pointer(error.absolute_schema_path, prefix="#"),
        keyword=str(error.validator),
        message=error.message,
    )


def _missing_required(errors: Iterable[ValidationError]) -> list[str]:
    missing: list[str] = []
    for error in errors:
        if error.validator != "required":
            continue
        names = re.findall(r"'([^']+)'", error.message)
        parent_path = _json_pointer(error.absolute_path)
        for name in names:
            field = f"{parent_path}/{_escape_pointer(name)}" if parent_path else name
            if field not in missing:
                missing.append(field)
    return missing


def _invalid_types(errors: Iterable[ValidationError]) -> list[InvalidTypeDetail]:
    invalid: list[InvalidTypeDetail] = []
    for error in errors:
        if error.validator != "type":
            continue
        expected_value = error.validator_value
        expected = (
            [str(value) for value in expected_value]
            if isinstance(expected_value, list)
            else [str(expected_value)]
        )
        field = _json_pointer(error.absolute_path) or "$"
        invalid.append(
            InvalidTypeDetail(
                field=field.removeprefix("/") if "/" not in field[1:] else field,
                expected_display=" | ".join(expected),
                actual=_detect_type(error.instance),
            )
        )
    return invalid


def _unknown_keys(errors: Iterable[ValidationError]) -> list[str]:
    unknown: list[str] = []
    for error in errors:
        if error.validator != "additionalProperties":
            continue
        parent_path = _json_pointer(error.absolute_path)
        for name in re.findall(r"'([^']+)'", error.message):
            field = f"{parent_path}/{_escape_pointer(name)}" if parent_path else name
            if field not in unknown:
                unknown.append(field)
    return unknown


def _validation_message(
    schema_errors: list[SchemaErrorDetail],
    missing_required: list[str],
    invalid_types: list[InvalidTypeDetail],
    unknown_keys: list[str],
) -> str:
    parts: list[str] = []
    if missing_required:
        parts.append(f"missing required: {', '.join(missing_required)}")
    if invalid_types:
        parts.append(
            "; ".join(
                f"{error.field}: expected {error.expected_display}, got {error.actual}"
                for error in invalid_types
            )
        )
    if unknown_keys:
        parts.append(f"unknown keys: {', '.join(unknown_keys)}")

    extra_errors = [
        error
        for error in schema_errors
        if error.keyword not in {"required", "type", "additionalProperties"}
    ]
    if extra_errors:
        parts.append(
            "; ".join(
                f"{error.instancePath or '/'}: {error.message}"
                for error in extra_errors
            )
        )
    return f"Workflow input validation failed: {' | '.join(parts)}"


def _json_pointer(path: Iterable[Any], prefix: str = "") -> str:
    parts = [_escape_pointer(str(part)) for part in path]
    pointer = "/" + "/".join(parts) if parts else ""
    return f"{prefix}{pointer}"


def _escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _detect_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _display_field(instance_path: str) -> str:
    if not instance_path:
        return "$"
    field = instance_path.removeprefix("/")
    return instance_path if "/" in field else field


def _value_at_pointer(value: Any, pointer: str) -> Any:
    current = value
    if not pointer:
        return current
    for raw_part in pointer.removeprefix("/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            return None
    return current


def _schema_path_for_instance(
    schema: Mapping[str, Any],
    instance_path: str,
    keyword: str,
) -> str:
    current: Any = schema
    schema_path: list[str | int] = []
    parts = (
        [
            part.replace("~1", "/").replace("~0", "~")
            for part in instance_path.removeprefix("/").split("/")
        ]
        if instance_path
        else []
    )

    for part in parts:
        if not isinstance(current, Mapping):
            return ""
        properties = current.get("properties")
        if isinstance(properties, Mapping) and part in properties:
            current = properties[part]
            schema_path.extend(("properties", part))
            continue
        items = current.get("items")
        if isinstance(items, Mapping) and part.isdigit():
            current = items
            schema_path.append("items")
            continue
        pattern_properties = current.get("patternProperties")
        if isinstance(pattern_properties, Mapping):
            match = next(
                (
                    (pattern, child)
                    for pattern, child in pattern_properties.items()
                    if re.search(str(pattern), part)
                ),
                None,
            )
            if match is not None:
                pattern, current = match
                schema_path.extend(("patternProperties", str(pattern)))
                continue
        return ""

    if isinstance(current, Mapping) and keyword in current:
        schema_path.append(keyword)
        return _json_pointer(schema_path, prefix="#")
    return ""
