from pathlib import Path

from sybil.serie import Serie

from app.utils.dicom_series import find_dicom_series
from app.utils.sybil_epi import (
    calculate_sybil_epi_score,
    epi_input_from_individual_data,
)


def run_sybil_pipeline(model, individual) -> tuple[float, str | None]:
    """
    Pure inference pipeline:
    - no UI
    - no threading
    - no shared state
    - deterministic output

    Returns the EPI score and, when CT inference ran, the label of the
    series that was used (``None`` for a precomputed six_year_risk row) —
    callers persist that label so a multi-series folder's automatic choice
    is auditable in batch output.
    """

    # A precomputed 6-year Sybil score skips CT inference entirely — mirrors
    # SybilController.run()'s single-individual branch.
    if individual.six_year_risk is not None:
        epi_in = epi_input_from_individual_data(individual, individual.six_year_risk)
        return calculate_sybil_epi_score(epi_in), None

    path = Path(individual.ct_scan_dir)

    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")

    series_list = find_dicom_series(path)

    if len(series_list) == 0:
        raise ValueError(f"No files found in: {path}")

    # A folder with more than one series (e.g. contrast + non-contrast) is
    # resolved automatically in batch mode — no UI to ask the user — by
    # picking the series with the most axial slices.
    series = max(series_list, key=lambda s: s.slice_count)

    serie = Serie(series.files)
    prediction = model.predict([serie])

    scores = prediction.scores[0]

    epi_in = epi_input_from_individual_data(individual, scores[5])
    return calculate_sybil_epi_score(epi_in), series.label
