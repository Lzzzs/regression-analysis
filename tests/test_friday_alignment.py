"""Tests for auto-aligning end_date to Friday."""
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from apps.api.orchestration import AutoJobOrchestrator


def _align_to_friday(d: date) -> date:
    """Expected behavior: roll back to most recent Friday on or before d."""
    while d.weekday() != 4:
        d -= timedelta(days=1)
    return d


class TestFridayAutoAlign:
    def test_wednesday_aligns_to_previous_friday(self):
        # 2026-03-25 is Wednesday -> should become 2026-03-20 (Friday)
        assert _align_to_friday(date(2026, 3, 25)) == date(2026, 3, 20)

    def test_friday_stays_friday(self):
        # 2026-03-27 is Friday -> stays
        assert _align_to_friday(date(2026, 3, 27)) == date(2026, 3, 27)

    def test_saturday_aligns_to_friday(self):
        # 2026-03-28 is Saturday -> 2026-03-27 (Friday)
        assert _align_to_friday(date(2026, 3, 28)) == date(2026, 3, 27)

    def test_orchestrator_no_longer_rejects_non_friday(self):
        """Submitting a Wednesday end_date should not raise ContractError."""
        mock_service = MagicMock()
        mock_snapshot_service = MagicMock()
        mock_snapshot_service.create_snapshot_from_providers.return_value = {"snapshot_id": "snap-test"}
        mock_service.create_job.return_value = {"job_id": "job-test", "status": "queued"}

        orch = AutoJobOrchestrator(mock_service, mock_snapshot_service)

        payload = {
            "weights": {"000001": 1.0},
            "start_date": "2025-03-26",
            "end_date": "2026-03-25",  # Wednesday — should NOT raise
            "rebalance_frequency": "monthly",
            "selected_assets": ["000001"],
            "assets": [{"code": "000001", "market": "cn", "asset_type": "stock"}],
        }
        # Should not raise
        result = orch.create_job_auto(payload)
        assert result["job_id"] == "job-test"

        # Verify the snapshot got the aligned Friday date
        snap_call = mock_snapshot_service.create_snapshot_from_providers.call_args[0][0]
        assert snap_call["week_end"] == "2026-03-20"  # aligned to Friday
