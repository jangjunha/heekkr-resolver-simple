import difflib
from typing import TypeVar


T = TypeVar("T")


def select_closest(candidates: list[tuple[T, str]], target: str) -> T:
    return max(
        *(
            (difflib.SequenceMatcher(None, target, candidate[1]).ratio(), candidate)
            for candidate in candidates
        ),
        key=lambda t: t[0],
    )[1][0]
