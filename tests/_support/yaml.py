from __future__ import annotations


def _parse_scalar(value: str):
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]

    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in ("null", "none"):
        return None

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def safe_load(stream):
    text = stream.read() if hasattr(stream, "read") else str(stream)
    lines = []
    for raw_line in text.splitlines():
        stripped = raw_line.split("#", 1)[0].rstrip()
        if stripped:
            lines.append(stripped)

    if not lines:
        return None

    if len(lines) == 1 and lines[0].strip() in ("{}", "[]"):
        return _parse_scalar(lines[0].strip())

    root = {}
    stack = [(-1, root)]

    for line in lines:
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if content.startswith("- "):
            raise NotImplementedError("Block lists are not supported by this lightweight YAML parser")

        if ":" not in content:
            raise ValueError(f"Invalid YAML line: {line}")

        key, raw_value = content.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if raw_value == "":
            value = {}
            parent[key] = value
            stack.append((indent, value))
        else:
            parent[key] = _parse_scalar(raw_value)

    return root
