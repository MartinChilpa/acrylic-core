from django.test import SimpleTestCase
from unittest.mock import patch

from chartmetric.engine import Chartmetric


class ChartmetricTrackMostHistoryTests(SimpleTestCase):
    def test_extracts_first_value_as_track_virality(self):
        cm = Chartmetric(refresh_token="test")
        sample = {
            "obj": [
                {
                    "domain": "chartmetric",
                    "track_domain_id": "16092909",
                    "type": "score",
                    "data": [
                        {"value": 95.00621, "timestp": "2025-10-12", "diff": None},
                        {"value": 94.1, "timestp": "2025-10-11", "diff": -0.9},
                    ],
                }
            ]
        }

        with patch.object(Chartmetric, "get_track_chartmetric_stats_most_history", return_value=sample):
            out = cm.get_track_virality("16092909")

        self.assertAlmostEqual(out, 95.00621, places=6)

    def test_returns_none_when_no_data(self):
        cm = Chartmetric(refresh_token="test")
        sample = {"obj": [{"domain": "chartmetric", "type": "score", "data": []}]}

        with patch.object(Chartmetric, "get_track_chartmetric_stats_most_history", return_value=sample):
            out = cm.get_track_virality("1")

        self.assertIsNone(out)
