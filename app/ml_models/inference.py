from datetime import datetime, timedelta
from functools import lru_cache
import os
from pathlib import Path
import warnings

import joblib
import numpy as np
from threadpoolctl import threadpool_limits


MODEL_DIR = Path(__file__).resolve().parent
MODEL_KEYS = ("ventilation", "pumps")
DAY_SECONDS = 86_400.0
EPOCH = datetime(1970, 1, 1)
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))


@lru_cache(maxsize=2)
def load_bundle(model_key: str):
    if model_key not in MODEL_KEYS:
        raise ValueError("Неизвестная модель")
    return joblib.load(MODEL_DIR / f"{model_key}.joblib")


def model_for_channel(channel_id: int) -> str | None:
    matches = [
        model_key for model_key in MODEL_KEYS
        if channel_id in load_bundle(model_key)["channel_codes"]
    ]
    if len(matches) > 1:
        raise ValueError("Канал одновременно зарегистрирован в нескольких моделях")
    return matches[0] if matches else None


@lru_cache(maxsize=1)
def supported_channels() -> dict[int, str]:
    result = {}
    for model_key in MODEL_KEYS:
        for channel_id in load_bundle(model_key)["channel_codes"]:
            if channel_id in result:
                raise ValueError("Канал одновременно зарегистрирован в нескольких моделях")
            result[channel_id] = model_key
    return result


def registered_object_id(bundle, channel_id: int) -> int | None:
    return next(
        (row["object_id"] for row in bundle["registry"] if row["channel"] == channel_id),
        None,
    )


def predict_failure(bundle, channel_id, forecast_at, fault_times, has_recent_object_data):
    result = {
        "model_version": bundle["model_version"],
        "forecast_at": forecast_at,
        "target_from": forecast_at + timedelta(hours=bundle["lead_hours"]),
        "target_until": forecast_at + timedelta(
            hours=bundle["lead_hours"] + bundle["window_hours"]
        ),
        "risk_score": None,
        "threshold": float(bundle["threshold"]),
        "warning": None,
    }
    if not fault_times:
        return {**result, "status": "insufficient_history"}
    cutoff = (forecast_at - EPOCH).total_seconds()
    raw = np.array(sorted((item - EPOCH).total_seconds() for item in fault_times), dtype=np.float64)
    if raw[-1] >= cutoff - bundle["quiet_hours"] * 3600:
        return {**result, "status": "recent_alarm_failure"}
    if not has_recent_object_data:
        return {**result, "status": "no_recent_object_data"}

    starts = raw[np.r_[True, np.diff(raw) > DAY_SECONDS]]
    previous = np.searchsorted(starts, cutoff, side="left") - 1
    previous_raw = np.searchsorted(raw, cutoff, side="left") - 1
    age = (cutoff - starts[previous]) / DAY_SECONDS if previous >= 0 else 3650.0
    raw_age = (cutoff - raw[previous_raw]) / DAY_SECONDS if previous_raw >= 0 else 3650.0
    last_gap = 3650.0
    mean_gap = 3650.0
    if previous >= 1:
        gaps = np.r_[0.0, np.diff(starts) / DAY_SECONDS]
        last_gap = gaps[previous]
        right = previous + 1
        left = max(right - 3, 1)
        mean_gap = float(gaps[left:right].mean())
    values = {
        "channel_code": float(bundle["channel_codes"][channel_id]),
        "age_days": min(age, 3650.0),
        "raw_age_days": min(raw_age, 3650.0),
        "last_gap_days": last_gap,
        "mean_last_gaps_days": mean_gap,
        "age_gap_ratio": age / max(mean_gap, 1.0),
    }
    for days in (7, 30, 90, 365):
        values[f"episodes_{days}d"] = float(
            np.searchsorted(starts, cutoff) - np.searchsorted(starts, cutoff - days * DAY_SECONDS)
        )
    weekday = forecast_at.weekday()
    month = forecast_at.month - 1
    values.update(
        weekday_sin=np.sin(2 * np.pi * weekday / 7),
        weekday_cos=np.cos(2 * np.pi * weekday / 7),
        month_sin=np.sin(2 * np.pi * month / 12),
        month_cos=np.cos(2 * np.pi * month / 12),
    )
    matrix = np.array([[values[name] for name in bundle["features"]]], dtype=np.float32)
    with warnings.catch_warnings(), threadpool_limits(limits=1):
        warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")
        score = float(bundle["estimator"].predict_proba(matrix)[0, 1])
    return {
        **result,
        "status": "ok",
        "risk_score": score,
        "warning": score >= bundle["threshold"],
    }
