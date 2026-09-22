from datetime import datetime, timedelta

from app.ml_models.inference import load_bundle, model_for_channel, predict_failure


def test_real_models_predict_supported_channels():
    forecast_at = datetime(2026, 9, 24)
    cases = [(8812, "pumps"), (103904, "ventilation")]

    for channel_id, expected_model in cases:
        assert model_for_channel(channel_id) == expected_model
        result = predict_failure(
            load_bundle(expected_model),
            channel_id,
            forecast_at,
            [forecast_at - timedelta(days=120), forecast_at - timedelta(days=50)],
            True,
        )
        assert result["status"] == "ok"
        assert 0 <= result["risk_score"] <= 1
        assert result["target_from"] == forecast_at + timedelta(days=1)
        assert result["target_until"] == forecast_at + timedelta(days=31)


def test_prediction_reports_insufficient_history():
    result = predict_failure(
        load_bundle("pumps"), 8812, datetime(2026, 9, 24), [], True,
    )
    assert result["status"] == "insufficient_history"
    assert result["risk_score"] is None
    assert result["warning"] is None
