from pathlib import Path

from sybil.serie import Serie

from app.utils.sybil_epi import (
    calculate_sybil_epi_score,
    epi_input_from_individual_data,
)


def run_sybil_pipeline(model, individual) -> float:
    """
    Pure inference pipeline:
    - no UI
    - no threading
    - no shared state
    - deterministic output
    """

    # A precomputed 6-year Sybil score skips CT inference entirely — mirrors
    # SybilController.run()'s single-individual branch.
    if individual.six_year_risk is not None:
        epi_in = epi_input_from_individual_data(individual, individual.six_year_risk)
        return calculate_sybil_epi_score(epi_in)

    path = Path(individual.ct_scan_dir)

    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")

    dicoms = sorted([f for f in path.iterdir() if f.is_file()])

    if len(dicoms) == 0:
        raise ValueError(f"No files found in: {path}")

    serie = Serie([str(f) for f in dicoms])
    prediction = model.predict([serie])

    scores = prediction.scores[0]

    epi_in = epi_input_from_individual_data(individual, scores[5])
    return calculate_sybil_epi_score(epi_in)
