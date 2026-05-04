"""Tests for SybilValidator."""

import pytest

from app.utils.validators import SybilValidator


@pytest.fixture
def v():
    return SybilValidator()


# ── required ──────────────────────────────────────────────────────────────────


class TestRequired:
    def test_non_empty_string_passes(self):
        assert SybilValidator.required("hello", "Field") == []

    def test_empty_string_fails(self):
        errors = SybilValidator.required("", "Age")
        assert errors == ["Age is required"]

    def test_whitespace_only_fails(self):
        errors = SybilValidator.required("   ", "BMI")
        assert errors == ["BMI is required"]

    def test_zero_string_passes(self):
        assert SybilValidator.required("0", "Value") == []

    def test_field_name_appears_in_error(self):
        errors = SybilValidator.required("", "Smoking duration")
        assert "Smoking duration" in errors[0]


# ── to_float ──────────────────────────────────────────────────────────────────


class TestToFloat:
    def test_integer_string_converts(self):
        result = SybilValidator.to_float("42", "Age")
        assert result.value == pytest.approx(42.0)
        assert result.errors == []

    def test_float_string_converts(self):
        result = SybilValidator.to_float("3.14", "BMI")
        assert result.value == pytest.approx(3.14)
        assert result.errors == []

    def test_negative_float_converts(self):
        result = SybilValidator.to_float("-1.5", "X")
        assert result.value == pytest.approx(-1.5)

    def test_non_numeric_string_fails(self):
        result = SybilValidator.to_float("abc", "Age")
        assert result.value is None
        assert result.errors == ["Age must be a number"]

    def test_empty_string_fails(self):
        result = SybilValidator.to_float("", "BMI")
        assert result.value is None
        assert result.errors

    def test_field_name_in_error(self):
        result = SybilValidator.to_float("xyz", "Smoking intensity")
        assert "Smoking intensity" in result.errors[0]


# ── range ─────────────────────────────────────────────────────────────────────


class TestRange:
    def test_value_within_range_passes(self):
        assert SybilValidator.range(50.0, "Age", 0, 200) == []

    def test_value_at_lower_bound_passes(self):
        assert SybilValidator.range(0.0, "Age", 0, 200) == []

    def test_value_at_upper_bound_passes(self):
        assert SybilValidator.range(200.0, "Age", 0, 200) == []

    def test_value_below_range_fails(self):
        errors = SybilValidator.range(-1.0, "Age", 0, 200)
        assert errors

    def test_value_above_range_fails(self):
        errors = SybilValidator.range(201.0, "Age", 0, 200)
        assert errors

    def test_error_contains_bounds(self):
        errors = SybilValidator.range(999.0, "BMI", 0, 100)
        assert "0" in errors[0] and "100" in errors[0]

    def test_field_name_in_error(self):
        errors = SybilValidator.range(-5.0, "Smoking duration", 0, 200)
        assert "Smoking duration" in errors[0]


# ── validate_field (full pipeline) ───────────────────────────────────────────


class TestValidateField:
    def test_valid_value_returns_float_and_no_errors(self, v):
        value, errors = v.validate_field("55", "Age", 0, 200)
        assert value == pytest.approx(55.0)
        assert errors == []

    def test_empty_value_returns_required_error(self, v):
        value, errors = v.validate_field("", "Age", 0, 200)
        assert value is None
        assert any("required" in e.lower() for e in errors)

    def test_non_numeric_returns_conversion_error(self, v):
        value, errors = v.validate_field("abc", "Age", 0, 200)
        assert value is None
        assert any("number" in e.lower() for e in errors)

    def test_out_of_range_returns_range_error(self, v):
        value, errors = v.validate_field("999", "Age", 0, 200)
        assert errors
        assert any("between" in e.lower() for e in errors)

    def test_no_range_bounds_skips_range_check(self, v):
        value, errors = v.validate_field("9999", "X")
        assert value == pytest.approx(9999.0)
        assert errors == []

    def test_only_min_bound_none_skips_range(self, v):
        # When either bound is None, range check is skipped
        value, errors = v.validate_field("9999", "X", None, None)
        assert errors == []

    def test_boundary_values_pass(self, v):
        value, errors = v.validate_field("0", "Age", 0, 200)
        assert errors == []
        value, errors = v.validate_field("200", "Age", 0, 200)
        assert errors == []

    def test_whitespace_value_fails_required(self, v):
        value, errors = v.validate_field("   ", "BMI", 0, 100)
        assert value is None
        assert errors

    def test_returns_only_first_error_category(self, v):
        # Empty string → required error only, no conversion error stacked on top
        _, errors = v.validate_field("", "Age", 0, 200)
        assert len(errors) == 1

    def test_float_decimal_precision(self, v):
        value, errors = v.validate_field("22.567", "BMI", 0, 100)
        assert value == pytest.approx(22.567)
        assert errors == []
