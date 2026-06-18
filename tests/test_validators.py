import pytest

from app.utils.validators import (
    BatchIntegralRowParser,
    BatchSybilRowParser,
    FieldParser,
    ParseError,
)

# ---------------------------------------------------------------------------
# ParseError
# ---------------------------------------------------------------------------


def test_parse_error_string_representation():
    err = ParseError("age", "Age is required")

    assert err.field == "age"
    assert err.message == "Age is required"
    assert str(err) == "age: Age is required"


# ---------------------------------------------------------------------------
# FieldParser.float
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("42", 42.0),
        ("3.14", 3.14),
        ("  7.5  ", 7.5),
        ("-1.2", -1.2),
        ("0", 0.0),
    ],
)
def test_float_valid_inputs(raw, expected):
    assert FieldParser.float("age", raw, "Age") == expected


@pytest.mark.parametrize(
    "raw,expected_msg",
    [
        ("", "Age is required"),
        ("   ", "Age is required"),
        ("abc", "Age must be a number"),
    ],
)
def test_float_invalid_inputs(raw, expected_msg):
    with pytest.raises(ParseError) as exc:
        FieldParser.float("age", raw, "Age")

    assert exc.value.field == "age"
    assert expected_msg in exc.value.message


# ---------------------------------------------------------------------------
# FieldParser.int
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1", 1),
        ("0", 0),
        ("42", 42),
    ],
)
def test_int_valid_inputs(raw, expected):
    assert FieldParser.int("x", raw, "X") == expected


@pytest.mark.parametrize(
    "raw,expected_msg",
    [
        ("", "required"),
        ("abc", "whole number"),
        ("3.14", "whole number"),
    ],
)
def test_int_invalid_inputs(raw, expected_msg):
    with pytest.raises(ParseError) as exc:
        FieldParser.int("x", raw, "X")

    assert exc.value.field == "x"
    assert expected_msg in exc.value.message


# ---------------------------------------------------------------------------
# FieldParser.optional_float
# ---------------------------------------------------------------------------


def test_optional_float_behavior():
    assert FieldParser.optional_float("x", "") is None
    assert FieldParser.optional_float("x", "   ") is None
    assert FieldParser.optional_float("x", "2.5") == 2.5


# ---------------------------------------------------------------------------
# FieldParser.required_str
# ---------------------------------------------------------------------------


def test_required_str_valid():
    assert FieldParser.required_str("name", " Alice ") == "Alice"


def test_required_str_invalid():
    with pytest.raises(ParseError):
        FieldParser.required_str("name", "   ")


# ---------------------------------------------------------------------------
# BatchSybilRowParser
# ---------------------------------------------------------------------------


def test_batch_sybil_row_parser_happy_path():
    row = {
        "age": "50",
        "bmi": "22.5",
        "smoking_duration": "10",
        "smoking_intensity": "5",
        "smoking_quit_time": "2",
        "copd": "1",
        "education": "3",
        "ethnicity": "2",
        "family_lc_history": "0",
        "personal_cancer_history": "0",
        "smoking_status": "1",
        "ct_scan_dir": "/tmp/scans",
        "six_year_risk": "0.12",
    }

    result = BatchSybilRowParser.parse(row)

    assert result["age"] == 50.0
    assert result["bmi"] == 22.5
    assert result["smoking_duration"] == 10.0
    assert result["copd"] == 1
    assert result["education"] == 3
    assert result["ct_scan_dir"] == "/tmp/scans"
    assert result["six_year_risk"] == 0.12


def test_batch_sybil_row_parser_missing_required_field():
    row = {
        "age": "abc",  # invalid float
    }

    with pytest.raises(ParseError) as exc:
        BatchSybilRowParser.parse(row)

    assert exc.value.field == "age"


# ---------------------------------------------------------------------------
# BatchIntegralRowParser
# ---------------------------------------------------------------------------


def test_batch_integral_row_parser_happy_path():
    row = {
        "bmi": "21.2",
        "age": "60",
        "female": "1",
        "fhlc": "0",
        "copdemph": "1",
        "formersmk": "0",
        "duration": "10",
        "cigday": "5",
        "quittime": "2",
        "image_file": "img.nii",
        "mask_file": "mask.nii",
    }

    result = BatchIntegralRowParser.parse(row)

    assert result["bmi"] == 21.2
    assert result["age"] == 60
    assert result["female"] == 1
    assert result["image_file"] == "img.nii"
    assert result["mask_file"] == "mask.nii"


def test_batch_integral_row_parser_optional_files():
    row = {
        "bmi": "21.2",
        "age": "60",
        "female": "1",
        "fhlc": "0",
        "copdemph": "1",
        "formersmk": "0",
        "duration": "10",
        "cigday": "5",
        "quittime": "2",
    }

    result = BatchIntegralRowParser.parse(row)

    assert result["image_file"] is None
    assert result["mask_file"] is None


def test_batch_integral_row_parser_invalid_input():
    row = {
        "bmi": "abc",  # invalid float
    }

    with pytest.raises(ParseError) as exc:
        BatchIntegralRowParser.parse(row)

    assert exc.value.field == "bmi"
