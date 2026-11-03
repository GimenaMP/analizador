from .maga_scraper import fetch_maga_white_corn_price

try:
    from .data_fetcher import fetch_weather, fetch_macro
    from .soil_balance import SoilProfile, bucket_series, simulate_window, build_dataset
    from .models import (
        make_xgb,
        make_logit,
        cross_validate,
        train_calibrated_model,
        enso_phase,
        semaforo,
        proyectar_futuro,
    )
    from .agronomy_economics import (
        TerrainModel,
        calculate_sowing_density,
        calculate_financial_projection,
    )
    from .input_validator import (
        ValidatedInput,
        ValidationError,
        validate_and_sanitize,
        sanitize_string,
        get_validation_summary,
    )
    from .rain_streak_analyzer import (
        StageAnalysis,
        RainStreakReport,
        HistoricalStreakSummary,
        analyze_rain_streaks,
        analyze_historical_streaks,
        generate_streak_pdf_section,
    )
except ImportError as e:
    # Soporte ligero para ejecuciones básicas de scraping o servidor ligero sin dependencias pesadas
    pass

__all__ = [
    "fetch_maga_white_corn_price",
    "fetch_weather",
    "fetch_macro",
    "SoilProfile",
    "bucket_series",
    "simulate_window",
    "build_dataset",
    "make_xgb",
    "make_logit",
    "cross_validate",
    "train_calibrated_model",
    "enso_phase",
    "semaforo",
    "proyectar_futuro",
    "TerrainModel",
    "calculate_sowing_density",
    "calculate_financial_projection",
    "ValidatedInput",
    "ValidationError",
    "validate_and_sanitize",
    "sanitize_string",
    "get_validation_summary",
    "StageAnalysis",
    "RainStreakReport",
    "HistoricalStreakSummary",
    "analyze_rain_streaks",
    "analyze_historical_streaks",
    "generate_streak_pdf_section",
]
