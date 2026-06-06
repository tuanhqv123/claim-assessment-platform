"""Deep side-by-side diff between two tenant configs."""

from __future__ import annotations

from typing import Any

_MISSING = object()

# Sentinel emitted in diff output for a key/index that exists on only one side,
# so an added/removed key is distinguishable from a real `None` value.
ABSENT = "<absent>"


def _walk(a: Any, b: Any, path: str, out: list[dict]) -> None:
    if isinstance(a, dict) or isinstance(b, dict):
        a_dict = a if isinstance(a, dict) else {}
        b_dict = b if isinstance(b, dict) else {}
        if not isinstance(a, dict) or not isinstance(b, dict):
            # Type mismatch at this node (one side isn't a dict).
            out.append({"path": path, "a_value": a, "b_value": b})
            return
        for key in sorted(set(a_dict) | set(b_dict)):
            child = f"{path}.{key}" if path else key
            av = a_dict.get(key, _MISSING)
            bv = b_dict.get(key, _MISSING)
            if av is _MISSING:
                out.append({"path": child, "a_value": ABSENT, "b_value": bv})
            elif bv is _MISSING:
                out.append({"path": child, "a_value": av, "b_value": ABSENT})
            else:
                _walk(av, bv, child, out)
        return

    if isinstance(a, list) or isinstance(b, list):
        if not isinstance(a, list) or not isinstance(b, list):
            out.append({"path": path, "a_value": a, "b_value": b})
            return
        if a != b:
            length = max(len(a), len(b))
            for i in range(length):
                child = f"{path}[{i}]"
                av = a[i] if i < len(a) else _MISSING
                bv = b[i] if i < len(b) else _MISSING
                if av is _MISSING:
                    out.append({"path": child, "a_value": ABSENT, "b_value": bv})
                elif bv is _MISSING:
                    out.append({"path": child, "a_value": av, "b_value": ABSENT})
                else:
                    _walk(av, bv, child, out)
        return

    if a != b:
        out.append({"path": path, "a_value": a, "b_value": b})


def diff_configs(a: dict, b: dict) -> list[dict]:
    """Return a list of {path, a_value, b_value} for every difference between a and b."""
    out: list[dict] = []
    _walk(a, b, "", out)
    return out
