"""Sybil-EPI lung cancer risk scoring model.

Combines Sybil's 6-year CT-based risk score with clinical/epidemiological
features to produce a calibrated ensemble probability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.individual_model import SybilInputData

# ---------------------------------------------------------------------------
# Ensemble model coefficients
# ---------------------------------------------------------------------------

_MODELS = [
    {
        "age": 0.03845109195667474,
        "bmi": -0.011386701750456835,
        "copd": 0.12928759691449734,
        "education": -0.05193241731109689,
        "black": 0.03305640252878926,
        "asian": 0.09784445590297448,
        "others": 0.13376957580540885,
        "family_history": 0.18966350529865886,
        "personal_history": 0.2668466804813831,
        "duration": 0.055840209011267156,
        "intensity": 0.018940450434839624,
        "quit_time": -0.010966650538136802,
        "smoking_status": 0.03685968494515114,
        "sybil_score": 7.07449145402105,
        "intercept": -8.525320331381652,
    },
    {
        "age": 0.002303841392360946,
        "bmi": -0.01680547871511917,
        "copd": 0.10504996934293911,
        "education": -0.05672137897042658,
        "black": 0.1247465020582522,
        "asian": 0.31053132298073605,
        "others": 0.04422649545382128,
        "family_history": 0.14122733134219667,
        "personal_history": 0.289612052253064,
        "duration": 0.05113662057588997,
        "intensity": 0.021528391225740278,
        "quit_time": -0.005483904343055354,
        "smoking_status": 0.12208435665482772,
        "sybil_score": 7.102737075603964,
        "intercept": -5.891646079306138,
    },
    {
        "age": -0.009365227121743586,
        "bmi": -0.017584596485864287,
        "copd": 0.06135975879299179,
        "education": -0.027680922143483815,
        "black": -0.030752160714064197,
        "asian": 0.35640978236750337,
        "others": 0.29538589515606223,
        "family_history": 0.06287967286709237,
        "personal_history": 0.26082109670718695,
        "duration": 0.05339280084623994,
        "intensity": 0.01826066070397732,
        "quit_time": -0.010139590639593188,
        "smoking_status": 0.1118991589544295,
        "sybil_score": 7.091749157821932,
        "intercept": -5.1618360151227565,
    },
    {
        "age": -0.022391589940648524,
        "bmi": -0.015141864095520916,
        "copd": 0.35096463025956043,
        "education": -0.0441341068232818,
        "black": 0.09996871364164378,
        "asian": 0.18279394664484774,
        "others": 0.2420325052464591,
        "family_history": 0.10343528034088861,
        "personal_history": 0.289568645309188,
        "duration": 0.06454349668304118,
        "intensity": 0.018565514462705858,
        "quit_time": 0.00021373176327254057,
        "smoking_status": 0.1527508244415102,
        "sybil_score": 7.2306869642905,
        "intercept": -4.9212850421682175,
    },
    {
        "age": 0.09548366831836427,
        "bmi": -0.021010852653676554,
        "copd": 0.2784018231289838,
        "education": -0.026466076415995972,
        "black": 0.27518174026893594,
        "asian": -0.009449283066505765,
        "others": -0.4221032657377639,
        "family_history": 0.04613280932621084,
        "personal_history": 0.20970214591522598,
        "duration": 0.06379394350343039,
        "intensity": 0.021895045879674575,
        "quit_time": 0.0025949273006358083,
        "smoking_status": 0.217206886709768,
        "sybil_score": 7.58715314980656,
        "intercept": -12.048447149368291,
    },
]

_CALIBRATORS = [
    {"a": -1.2329771175814760, "b": -1.68791783871881180},
    {"a": -1.1765657141893946, "b": -0.67770947946629200},
    {"a": -1.2563689611941198, "b": -0.71005858953171520},
    {"a": -1.0269780235235613, "b": 0.02051234177619454},
    {"a": -0.8470538501992946, "b": 1.75067111594711300},
]


@dataclass
class EpiInput:
    """Inputs required by the Sybil-EPI scoring function.

    Constructed from :class:`~app.models.SybilInputData` plus the
    6-year risk score returned by the Sybil CT model.
    """

    age: float
    bmi: float
    copd: int  # 0 or 1
    education: int  # 1-6
    ethnicity: str  # "White" | "Black" | "Asian" | "Others"
    family_history: int  # 0 or 1
    personal_history: int  # 0 or 1
    smoking_duration: float
    smoking_intensity: float
    smoking_quit: float
    smoking_status: int  # 0 = former, 1 = current
    risk_sybil_6_year: float  # 0.0-1.0, from Sybil CT prediction


def calculate_sybil_epi_score(inputs: EpiInput) -> float:
    """Compute the Sybil-EPI ensemble risk score.

    Runs the linear model + Platt calibration for each of the five ensemble
    members and returns their mean probability.

    Args:
        inputs: A fully populated :class:`EpiInput` instance.

    Returns:
        Calibrated lung cancer risk probability in [0, 1].
    """
    ethnicity_key = inputs.ethnicity  # already "White" / "Black" / "Asian" / "Others"

    total_prob = 0.0
    for model, calib in zip(_MODELS, _CALIBRATORS, strict=False):
        if ethnicity_key == "Asian":
            ethnicity_coeff = model["asian"]
        elif ethnicity_key == "Black":
            ethnicity_coeff = model["black"]
        elif ethnicity_key == "Others":
            ethnicity_coeff = model["others"]
        else:
            ethnicity_coeff = 0.0  # White is the reference category

        z = (
            inputs.risk_sybil_6_year * model["sybil_score"]
            + inputs.age * model["age"]
            + inputs.bmi * model["bmi"]
            + inputs.copd * model["copd"]
            + inputs.education * model["education"]
            + ethnicity_coeff
            + inputs.family_history * model["family_history"]
            + inputs.personal_history * model["personal_history"]
            + inputs.smoking_duration * model["duration"]
            + inputs.smoking_intensity * model["intensity"]
            + inputs.smoking_quit * model["quit_time"]
            + inputs.smoking_status * model["smoking_status"]
            + model["intercept"]
        )

        p_calibrated = 1.0 / (1.0 + math.exp(calib["a"] * z + calib["b"]))
        total_prob += p_calibrated

    return total_prob / len(_MODELS)


def epi_input_from_individual_data(
    individual: SybilInputData,
    sybil_6_year_score: float,
) -> EpiInput:
    """Build an :class:`EpiInput` from form data and the Sybil CT score.

    Args:
        individual: Validated individual data from the input form.
        sybil_6_year_score: The 6-year risk probability from Sybil (0-1).

    Returns:
        A ready-to-score :class:`EpiInput` instance.
    """

    return EpiInput(
        age=individual.age,
        bmi=individual.bmi,
        copd=individual.copd,
        education=individual.education,
        ethnicity=individual.ethnicity,
        family_history=individual.family_lc_history,
        personal_history=individual.personal_cancer_history,
        smoking_duration=individual.smoking_duration,
        smoking_intensity=individual.smoking_intensity,
        smoking_quit=individual.smoking_quit_time,
        smoking_status=individual.smoking_status,
        risk_sybil_6_year=sybil_6_year_score,
    )
