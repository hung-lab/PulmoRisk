from dataclasses import dataclass, field

from app.config.settings import PROJECT_ROOT


@dataclass
class SybilInputData:
    age: int
    bmi: float
    copd: int
    education: int
    ethnicity: int
    family_lc_history: int
    personal_cancer_history: int
    smoking_duration: float
    smoking_intensity: float
    smoking_quit_time: float
    smoking_status: int
    ct_scan_dir: str | None = PROJECT_ROOT
    six_year_risk: float | None = None


@dataclass
class RiskResult:
    yearly_scores: list[float]
    epi_score: float


@dataclass
class IntegralClinicalData:
    epi_age: int
    epi_female: int
    epi_fhlc: int
    epi_copdemph: int
    epi_formersmk: int
    epi_duration: float
    epi_cigday: float
    epi_quittime: float
    epi_bmi: float

    study: str | None = None
    pid: str | None = None
    nid: str | None = None


@dataclass
class RadiomicsFeatures:
    features: dict[str, float] = field(default_factory=dict)


@dataclass
class IntegralRadiomicsInput:
    clinical: IntegralClinicalData
    radiomics: RadiomicsFeatures


@dataclass
class IntegralRiskResult:
    benign_probability: float
    malignant_probability: float
