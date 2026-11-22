from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from aegisops.telemetry.normalizer import NormalizerConfig, TelemetryNormalizer
from aegisops.telemetry.models import SourceType


def test_normalizer_maps_loki_response(mocker):
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {
        "status": "success",
        "data": {
            "result": [
                {
                    "stream": {"namespace": "online-boutique", "app": "frontend"},
                    "values": [
                        [str(int(datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc).timestamp() * 1e9)),
                         "error: failed to fetch"],
                    ],
                }
            ]
        },
    }

    with patch("httpx.Client.get", return_value=fake_response):
        cfg = NormalizerConfig(lookback=timedelta(minutes=5), metric_queries=())
        events = TelemetryNormalizer(cfg).collect()

    assert len(events) == 1
    assert events[0].source == SourceType.LOKI
    assert events[0].service == "frontend"
    assert events[0].severity.value == "high"  # 'error' in message