from dataclasses import dataclass


@dataclass
class ValidationResult:
    value: float | int | str | None
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


class IntegralValidator(SybilValidator):
    # ───────────────────────────── INT VALIDATION ─────────────────────────

    @staticmethod
    def to_int(value: str, name: str) -> ValidationResult:
        try:
            return ValidationResult(int(value), [])
        except ValueError:
            return ValidationResult(None, [f"{name} must be an integer"])

    # ───────────────────────────── BINARY VALIDATION ──────────────────────

    @staticmethod
    def binary(value: str, name: str) -> ValidationResult:
        try:
            v = int(value)
            if v not in (0, 1):
                return ValidationResult(None, [f"{name} must be 0 or 1"])
            return ValidationResult(v, [])
        except ValueError:
            return ValidationResult(None, [f"{name} must be 0 or 1"])

    # ───────────────────────────── DICT VALIDATION (RADIO) ────────────────

    @staticmethod
    def validate_radiomics(features: dict) -> list[str]:
        """
        Ensures radiomics payload is safe for R model.
        """
        errors = []

        if not isinstance(features, dict):
            return ["Radiomics must be a JSON object"]

        if len(features) == 0:
            return ["Radiomics features cannot be empty"]

        for k, v in features.items():
            if v is None:
                errors.append(f"{k} is missing")
                continue

            try:
                float(v)
            except Exception:
                errors.append(f"{k} must be numeric")

        return errors

    # ───────────────────────────── FULL PIPELINE HELPERS ──────────────────

    @classmethod
    def clinical_field(
        cls,
        value: str,
        name: str,
        min_v: float | None = None,
        max_v: float | None = None,
    ):
        return cls.validate_field(value, name, min_v, max_v)
