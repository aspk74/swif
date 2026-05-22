"""
Pure-function compliance comparator.

Evaluates whether a telemetry value satisfies a rule's expected_value
given a LogicOperator. All type coercion is handled here so the rest
of the pipeline deals only with booleans.
"""
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.schema import LogicOperator


def _try_numeric(value: str) -> float | None:
    """Attempt to cast a string to a number. Returns None on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def check_compliance(actual_value: str, expected_value: str, logic: LogicOperator) -> bool:
    """
    Evaluate whether `actual_value` satisfies `expected_value` under the given `logic`.

    Returns True if compliant, False if violated.

    For numeric operators (GT, GTE, LT, LTE), both values are cast to float.
    If casting fails, they fall back to lexicographic string comparison.
    """
    match logic:
        case LogicOperator.EQUALS:
            # Try numeric comparison first, fall back to string
            a_num, e_num = _try_numeric(actual_value), _try_numeric(expected_value)
            if a_num is not None and e_num is not None:
                return a_num == e_num
            return actual_value.strip().lower() == expected_value.strip().lower()

        case LogicOperator.NOT_EQUALS:
            a_num, e_num = _try_numeric(actual_value), _try_numeric(expected_value)
            if a_num is not None and e_num is not None:
                return a_num != e_num
            return actual_value.strip().lower() != expected_value.strip().lower()

        case LogicOperator.CONTAINS:
            return expected_value.lower() in actual_value.lower()

        case LogicOperator.NOT_CONTAINS:
            return expected_value.lower() not in actual_value.lower()

        case LogicOperator.GREATER_THAN:
            a_num, e_num = _try_numeric(actual_value), _try_numeric(expected_value)
            if a_num is not None and e_num is not None:
                return a_num > e_num
            return actual_value > expected_value  # lexicographic fallback

        case LogicOperator.GREATER_THAN_OR_EQUAL:
            a_num, e_num = _try_numeric(actual_value), _try_numeric(expected_value)
            if a_num is not None and e_num is not None:
                return a_num >= e_num
            return actual_value >= expected_value

        case LogicOperator.LESS_THAN:
            a_num, e_num = _try_numeric(actual_value), _try_numeric(expected_value)
            if a_num is not None and e_num is not None:
                return a_num < e_num
            return actual_value < expected_value

        case LogicOperator.LESS_THAN_OR_EQUAL:
            a_num, e_num = _try_numeric(actual_value), _try_numeric(expected_value)
            if a_num is not None and e_num is not None:
                return a_num <= e_num
            return actual_value <= expected_value

        case LogicOperator.REGEX_MATCH:
            try:
                return bool(re.fullmatch(expected_value, actual_value))
            except re.error:
                return False  # Treat bad regex as non-compliant

        case LogicOperator.EXISTS:
            # Compliant if value is non-empty
            return bool(actual_value and actual_value.strip())

        case LogicOperator.NOT_EXISTS:
            # Compliant if value is empty/absent
            return not bool(actual_value and actual_value.strip())

        case _:
            # Unknown operator — treat as non-compliant to be safe
            return False
