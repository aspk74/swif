"""
Unit tests for the compliance comparator.

Tests every LogicOperator variant with numeric, string, and edge cases.
"""
import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from validation.comparator import check_compliance
from db.schema import LogicOperator


class TestEquals:
    def test_string_equal(self):
        assert check_compliance("true", "true", LogicOperator.EQUALS) is True

    def test_string_not_equal(self):
        assert check_compliance("false", "true", LogicOperator.EQUALS) is False

    def test_numeric_equal(self):
        assert check_compliance("90", "90", LogicOperator.EQUALS) is True

    def test_numeric_equal_float(self):
        assert check_compliance("90.0", "90", LogicOperator.EQUALS) is True

    def test_case_insensitive(self):
        assert check_compliance("True", "true", LogicOperator.EQUALS) is True


class TestNotEquals:
    def test_different_values(self):
        assert check_compliance("false", "true", LogicOperator.NOT_EQUALS) is True

    def test_same_values(self):
        assert check_compliance("true", "true", LogicOperator.NOT_EQUALS) is False

    def test_numeric(self):
        assert check_compliance("100", "90", LogicOperator.NOT_EQUALS) is True


class TestContains:
    def test_substring_present(self):
        assert check_compliance("TLS1.2,TLS1.3", "TLS1.2", LogicOperator.CONTAINS) is True

    def test_substring_absent(self):
        assert check_compliance("TLS1.0", "TLS1.2", LogicOperator.CONTAINS) is False

    def test_case_insensitive(self):
        assert check_compliance("Enabled", "enabled", LogicOperator.CONTAINS) is True


class TestNotContains:
    def test_absent(self):
        assert check_compliance("TLS1.2", "SSLv3", LogicOperator.NOT_CONTAINS) is True

    def test_present(self):
        assert check_compliance("SSLv3,TLS1.0", "SSLv3", LogicOperator.NOT_CONTAINS) is False


class TestGreaterThan:
    def test_numeric_gt(self):
        assert check_compliance("100", "90", LogicOperator.GREATER_THAN) is True

    def test_numeric_equal(self):
        assert check_compliance("90", "90", LogicOperator.GREATER_THAN) is False

    def test_numeric_lt(self):
        assert check_compliance("80", "90", LogicOperator.GREATER_THAN) is False


class TestGreaterThanOrEqual:
    def test_gt(self):
        assert check_compliance("100", "90", LogicOperator.GREATER_THAN_OR_EQUAL) is True

    def test_equal(self):
        assert check_compliance("90", "90", LogicOperator.GREATER_THAN_OR_EQUAL) is True

    def test_lt(self):
        assert check_compliance("80", "90", LogicOperator.GREATER_THAN_OR_EQUAL) is False


class TestLessThan:
    def test_lt(self):
        assert check_compliance("80", "90", LogicOperator.LESS_THAN) is True

    def test_equal(self):
        assert check_compliance("90", "90", LogicOperator.LESS_THAN) is False

    def test_gt(self):
        assert check_compliance("100", "90", LogicOperator.LESS_THAN) is False


class TestLessThanOrEqual:
    def test_lt(self):
        assert check_compliance("80", "90", LogicOperator.LESS_THAN_OR_EQUAL) is True

    def test_equal(self):
        assert check_compliance("90", "90", LogicOperator.LESS_THAN_OR_EQUAL) is True

    def test_gt(self):
        assert check_compliance("100", "90", LogicOperator.LESS_THAN_OR_EQUAL) is False


class TestRegexMatch:
    def test_match(self):
        assert check_compliance("192.168.1.1", r"192\.168\.\d+\.\d+", LogicOperator.REGEX_MATCH) is True

    def test_no_match(self):
        assert check_compliance("10.0.0.1", r"192\.168\.\d+\.\d+", LogicOperator.REGEX_MATCH) is False

    def test_bad_regex(self):
        # Bad regex should return False (non-compliant) rather than crashing
        assert check_compliance("test", r"[invalid(", LogicOperator.REGEX_MATCH) is False


class TestExists:
    def test_non_empty(self):
        assert check_compliance("something", "", LogicOperator.EXISTS) is True

    def test_empty(self):
        assert check_compliance("", "", LogicOperator.EXISTS) is False

    def test_whitespace_only(self):
        assert check_compliance("   ", "", LogicOperator.EXISTS) is False


class TestNotExists:
    def test_empty(self):
        assert check_compliance("", "", LogicOperator.NOT_EXISTS) is True

    def test_non_empty(self):
        assert check_compliance("something", "", LogicOperator.NOT_EXISTS) is False
