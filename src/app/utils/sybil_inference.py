from pathlib import Path

from sybil.serie import Serie

from app.utils.sybil_epi import (
    calculate_sybil_epi_score,
    epi_input_from_patient_data,
)


def run_sybil_pipeline(model, patient) -> float:
    """
    Pure inference pipeline:
    - no UI
    - no threading
    - no shared state
    - deterministic output
    """

    path = Path(patient.ct_scan_dir)

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

    epi_in = epi_input_from_patient_data(patient, scores[5])
    return calculate_sybil_epi_score(epi_in)
