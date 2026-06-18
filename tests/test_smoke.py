"""Smoke tests — verify imports and core objects construct without crashing.

These tests do not require a display or a real Tk root. They are intentionally
shallow: if an import fails or a constructor raises unexpectedly, the test
fails immediately and points to the broken module.
"""

import sys
from unittest.mock import MagicMock

# ── Sybil mock — must be in place before any controller imports sybil ─────────
sys.modules.setdefault("sybil", MagicMock())
sys.modules.setdefault("sybil.serie", MagicMock())


# ── models ────────────────────────────────────────────────────────────────────


class TestModelImports:
    def test_sybil_input_data_imports(self):
        from app.models.individual_model import SybilInputData

        assert SybilInputData is not None

    def test_risk_result_imports(self):
        from app.models.individual_model import RiskResult

        assert RiskResult is not None

    def test_sybil_input_data_constructs(self):
        from app.models.individual_model import SybilInputData

        obj = SybilInputData(
            age=65,
            bmi=27.0,
            copd=0,
            education=3,
            ethnicity=1,
            family_lc_history=0,
            personal_cancer_history=0,
            smoking_duration=30.0,
            smoking_intensity=20.0,
            smoking_quit_time=5.0,
            smoking_status=0,
            ct_scan_dir="/tmp",
        )
        assert obj.age == 65

    def test_risk_result_constructs(self):
        from app.models.individual_model import RiskResult

        obj = RiskResult(yearly_scores=[0.01] * 6, epi_score=0.12)
        assert len(obj.yearly_scores) == 6


# ── utilities ─────────────────────────────────────────────────────────────────


class TestUtilityImports:
    def test_event_bus_imports(self):
        from app.utils.event_bus import EventBus, AppEvent

        assert EventBus is not None
        assert AppEvent is not None

    def test_app_event_constructs(self):
        from app.utils.event_bus import AppEvent

        e = AppEvent(type="log", message="hello")
        assert e.type == "log"

    def test_event_bus_constructs(self):
        from app.utils.event_bus import EventBus

        bus = EventBus(root=MagicMock())
        assert bus is not None

    def test_validator_imports(self):
        from app.utils.validators import (
            FieldParser,
            BatchSybilRowParser,
            BatchIntegralRowParser,
        )

        assert FieldParser is not None
        assert BatchSybilRowParser is not None
        assert BatchIntegralRowParser is not None

    def test_sybil_epi_imports(self):
        from app.utils.sybil_epi import (
            calculate_sybil_epi_score,
            epi_input_from_individual_data,
            EpiInput,
        )

        assert calculate_sybil_epi_score is not None
        assert epi_input_from_individual_data is not None
        assert EpiInput is not None

    def test_helpers_imports(self):
        from app.utils.helpers import center_window, resource_path, resolve_color

        assert center_window is not None
        assert resource_path is not None
        assert resolve_color is not None

    def test_settings_imports(self):
        from app.config.settings import (
            LEVEL_COLOURS,
            LEVEL_PREFIX,
            PRIMARY_LIGHT,
            PRIMARY_DARK,
            ACCENT_LIGHT,
            ACCENT_DARK,
            ERROR_COLOUR,
        )

        assert isinstance(LEVEL_COLOURS, dict)
        assert isinstance(LEVEL_PREFIX, dict)
        assert all(k in LEVEL_COLOURS for k in ("INFO", "SUCCESS", "WARNING", "ERROR"))
        assert all(k in LEVEL_PREFIX for k in ("INFO", "SUCCESS", "WARNING", "ERROR"))

    def test_ui_config_imports(self):
        from app.utils.ui_config import (
            SPACE_XS,
            SPACE_SM,
            SPACE_MD,
            SPACE_LG,
            SPACE_XL,
            INPUT_WIDTH,
            LABEL_WIDTH,
        )

        assert SPACE_XS < SPACE_SM < SPACE_MD < SPACE_LG < SPACE_XL


# ── controllers ───────────────────────────────────────────────────────────────


class TestControllerImports:
    def test_base_controller_imports(self):
        from app.controllers.base_controller import BaseController

        assert BaseController is not None

    def test_base_controller_constructs(self):
        from app.controllers.base_controller import BaseController
        from app.utils.event_bus import EventBus

        ctrl = BaseController(root=MagicMock(), bus=MagicMock())
        assert ctrl is not None

    def test_app_controller_imports(self):
        from app.controllers.app_controller import AppController

        assert AppController is not None

    def test_app_controller_constructs(self):
        from app.controllers.app_controller import AppController

        ctrl = AppController(
            root=MagicMock(),
            bus=MagicMock(),
            split_view=MagicMock(),
            sybil_form=MagicMock(),
        )
        assert ctrl is not None

    def test_menubar_controller_imports(self):
        from app.controllers.menubar_controller import MenuBarController

        assert MenuBarController is not None

    def test_menubar_controller_constructs(self):
        from app.controllers.menubar_controller import MenuBarController

        ctrl = MenuBarController(
            root=MagicMock(),
            bus=MagicMock(),
            controller=MagicMock(),
        )
        assert ctrl is not None

    def test_sybil_controller_imports(self):
        from app.controllers.sybil_controller import SybilController

        assert SybilController is not None

    def test_sybil_controller_constructs(self):
        from app.controllers.sybil_controller import SybilController

        ctrl = SybilController(root=MagicMock(), bus=MagicMock())
        assert ctrl is not None

    def test_sybil_controller_initial_state(self):
        from app.controllers.sybil_controller import SybilController

        ctrl = SybilController(root=MagicMock(), bus=MagicMock())
        assert ctrl._model is None
        assert ctrl._pending is None
        assert ctrl._infer_active is False


# ── event bus wiring ──────────────────────────────────────────────────────────


class TestEventBusWiring:
    def test_event_bus_subscribe_and_emit(self):
        from app.utils.event_bus import EventBus, AppEvent

        root = MagicMock()
        call_count = 0

        def after_once(delay, fn):
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                fn()  # run _poll exactly once, then stop

        root.after.side_effect = after_once

        bus = EventBus(root)
        received = []
        bus.subscribe(lambda e: received.append(e))
        bus.emit(AppEvent(type="log", message="smoke"))
        bus.start()

        assert len(received) == 1
        assert received[0].message == "smoke"

    def test_base_controller_log_reaches_bus(self):
        from app.controllers.base_controller import BaseController
        from app.utils.event_bus import AppEvent

        bus = MagicMock()
        ctrl = BaseController(root=MagicMock(), bus=bus)
        ctrl._log("smoke test message")

        event = bus.emit.call_args[0][0]
        assert event.type == "log"
        assert "smoke test message" in event.message

    def test_sybil_epi_round_trip(self):
        """EpiInput → calculate_sybil_epi_score returns a valid probability."""
        from app.utils.sybil_epi import EpiInput, calculate_sybil_epi_score

        epi = EpiInput(
            age=65.0,
            bmi=27.0,
            copd=0,
            education=3,
            ethnicity="White",
            family_history=0,
            personal_history=0,
            smoking_duration=30.0,
            smoking_intensity=20.0,
            smoking_quit=5.0,
            smoking_status=0,
            risk_sybil_6_year=0.05,
        )
        score = calculate_sybil_epi_score(epi)
        assert 0.0 < score < 1.0
