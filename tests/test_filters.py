from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from pdm_dockerize import filters


@dataclass
class FilterCase:
    id: str
    data: Any
    expected: list[str] | None = None
    error: type[Exception] | None = None


FILTER_CASES = (
    FilterCase("no-filter", None, []),
    FilterCase("str", "*", ["*"]),
    FilterCase("empty-str", "", []),
    FilterCase("list", ["some", "filters"], ["some", "filters"]),
    FilterCase("empty-list", [], []),
    FilterCase("bad-type", 42, error=TypeError),
    FilterCase("bad-inner-type", ["OK", 42], error=TypeError),
)


@pytest.mark.parametrize(
    "case",
    (
        pytest.param(
            case, id=case.id, marks=pytest.mark.xfail(raises=case.error) if case.error else ()
        )
        for case in FILTER_CASES
    ),
)
def test_parse_filters(case: FilterCase):
    assert filters.parse({"key": case.data}, "key") == case.expected
