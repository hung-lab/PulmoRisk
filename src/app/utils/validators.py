from dataclasses import dataclass


@dataclass
class ValidationResult:
    value: float | str | None
    errors: list[str]


class SybilValidator:
    # ── basic checks ─────────────────────────────

    @staticmethod
    def required(value: str, name: str) -> list[str]:
        if not value.strip():
            return [f"{name} is required"]
        return []

    @staticmethod
    def to_float(value: str, name: str) -> ValidationResult:
        try:
            return ValidationResult(float(value), [])
        except ValueError:
            return ValidationResult(None, [f"{name} must be a number"])

    @staticmethod
    def range(value: float, name: str, min_v: float, max_v: float) -> list[str]:
        if not (min_v <= value <= max_v):
            return [f"{name} must be between {min_v} and {max_v}"]
        return []

    # ── full field pipeline ─────────────────────

    @classmethod
    def validate_field(
        cls,
        value: str,
        name: str,
        min_v: float | None = None,
        max_v: float | None = None,
    ) -> tuple[float | None, list[str]]:

        errors = []

        # required
        errors += cls.required(value, name)
        if errors:
            return None, errors

        # float conversion
        result = cls.to_float(value, name)
        errors += result.errors
        if errors:
            return None, errors

        num = result.value

        # range check
        if min_v is not None and max_v is not None:
            errors += cls.range(num, name, min_v, max_v)

        return num, errors
