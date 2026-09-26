"""
Módulo de Machine Learning, Validación Temporal Cruzada y Proyección Estacional.
Entrena modelos XGBoost y Regresión Logística con validación GroupKFold por años,
calibración sigmoidea y cálculo de Brier Skill Score (BSS).
"""
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss

from config.settings import SoilConfig, SOIL_CONFIG, SemaforoConfig, SEMAFORO_CONFIG


def make_xgb() -> xgb.XGBClassifier:
    """Constructor de modelo de Gradient Boosting regularizado para series agroclimáticas."""
    return xgb.XGBClassifier(
        n_estimators=150,
        max_depth=2,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=20,
        reg_lambda=5.0,
        eval_metric="logloss",
        random_state=42
    )


def make_logit() -> Any:
    """Constructor de modelo de regresión logística regularizada con escalado estándar."""
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=1000, random_state=42))


def cross_validate(
    df: pd.DataFrame,
    feats: List[str],
    make_model_fn: Any,
    n_splits: int = 5
) -> Dict[str, Any]:
    """
    Validación cruzada agrupada por año completo para evaluar generalización temporal sin fuga.
    Calcula AUC, Brier Score y Brier Skill Score (BSS) respecto a la climatología local.
    """
    X = df[feats].astype(float).values
    y = df["target"].astype(int).values
    groups = df["year"].values

    oof = np.zeros(len(df))
    clim = np.zeros(len(df))

    gkf = GroupKFold(n_splits=n_splits)
    for tr, te in gkf.split(X, y, groups):
        m = make_model_fn().fit(X[tr], y[tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
        clim[te] = y[tr].mean()

    bs_model = brier_score_loss(y, oof)
    bs_clim = brier_score_loss(y, clim)
    bss = 1.0 - (bs_model / max(bs_clim, 1e-6))
    auc = roc_auc_score(y, oof)

    return {
        "auc": auc,
        "bss": bss,
        "brier_score": bs_model,
        "brier_clim": bs_clim,
        "oof": oof
    }


def train_calibrated_model(
    train_df: pd.DataFrame,
    features: List[str],
    make_model_fn: Any,
    n_splits: int = 5
) -> CalibratedClassifierCV:
    """Entrena y calibra las probabilidades del modelo final usando GroupKFold."""
    X = train_df[features].astype(float).values
    y = train_df["target"].astype(int).values
    groups = train_df["year"].values

    splits = list(GroupKFold(n_splits=n_splits).split(X, y, groups))
    calibrated = CalibratedClassifierCV(estimator=make_model_fn(), method="sigmoid", cv=splits)
    calibrated.fit(X, y)
    return calibrated


def enso_phase(mei: float) -> str:
    """Clasificación de fase del ciclo El Niño - Oscilación del Sur (ENSO)."""
    if pd.isna(mei):
        return "N/D"
    if mei >= 0.5:
        return "El Niño"
    elif mei <= -0.5:
        return "La Niña"
    return "Neutral"


def semaforo(
    prob: float,
    fase: str,
    sem_cfg: SemaforoConfig = SEMAFORO_CONFIG
) -> Tuple[str, str, str]:
    """
    Asigna el estado del semáforo agronómico de acuerdo con la probabilidad calibrada
    y los umbrales configurados en SemaforoConfig.
    Retorna: (Estado, Color, Acción recomendada).
    """
    if prob >= sem_cfg.prob_optimo_min:
        return (
            "ÓPTIMO",
            "Verde",
            "Condiciones hídricas altamente favorables. Proceder con la siembra en la densidad recomendada."
        )
    elif prob >= sem_cfg.prob_alerta_min:
        return (
            "CONDICIONADO O EN ALERTA",
            "Amarillo",
            "Riesgo hídrico moderado: emplear variedades precoces o tolerantes a sequía, labranza de conservación y monitoreo de humedad."
        )
    else:
        return (
            "NO SEMBRAR",
            "Rojo",
            f"Riesgo crítico de fracaso hídrico por sequía prolongada o anegamiento. Fase ENSO observada: {fase}."
        )


def proyectar_futuro(
    ds: pd.DataFrame,
    final_model: CalibratedClassifierCV,
    feats: List[str],
    horizon_months: int = 5,
    sem_cfg: SemaforoConfig = SEMAFORO_CONFIG
) -> List[Dict[str, Any]]:
    """
    Proyecta la viabilidad para los meses futuros combinando la última señal ENSO
    y la climatología histórica del mes correspondiente.
    """
    last_row = ds.dropna(subset=feats).iloc[-1]
    fecha_base = pd.to_datetime(last_row["time"])
    proyecciones = []

    for i in range(1, horizon_months + 1):
        fecha_futura = fecha_base + pd.DateOffset(months=i)
        m_fut = fecha_futura.month

        clima_mes = ds[ds["month"] == m_fut]
        if clima_mes.empty:
            continue

        vector_futuro = pd.Series({
            "precip_acc_15d": clima_mes["precip_acc_15d"].median(),
            "precip_acc_30d": clima_mes["precip_acc_30d"].median(),
            "balance_hidrico_30d": clima_mes["balance_hidrico_30d"].median(),
            "humedad_suelo_frac": clima_mes["humedad_suelo_frac"].median(),
            "dry_spell_len": clima_mes["dry_spell_len"].median(),
            "doy_sin": np.sin(2 * np.pi * fecha_futura.dayofyear / 365.25),
            "doy_cos": np.cos(2 * np.pi * fecha_futura.dayofyear / 365.25),
            "mei_lag1": last_row["mei_lag1"],
            "mei_trend": last_row["mei_trend"]
        })

        x_in = vector_futuro[feats].astype(float).values.reshape(1, -1)
        prob = float(final_model.predict_proba(x_in)[0, 1])
        estado, color, accion = semaforo(prob, enso_phase(vector_futuro["mei_lag1"]), sem_cfg=sem_cfg)

        proyecciones.append({
            "fecha": fecha_futura,
            "mes_nombre": fecha_futura.strftime("%B %Y"),
            "probabilidad": prob,
            "estado": estado,
            "color": color,
            "accion": accion,
            "fase_enso": enso_phase(vector_futuro["mei_lag1"])
        })

    return proyecciones
