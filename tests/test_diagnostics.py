"""Tests for diagnostics support for Marstek Local API."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from custom_components.marstek_local_api.const import DATA_COORDINATOR, DOMAIN
from custom_components.marstek_local_api import diagnostics


@pytest.fixture
def coordinator():
    """Mock MarstekDataUpdateCoordinator."""
    coordinator = diagnostics.MarstekDataUpdateCoordinator.__new__(
        diagnostics.MarstekDataUpdateCoordinator
    )

    coordinator.api = MagicMock()
    coordinator.api.get_all_command_stats.return_value = {
        "Bat.GetStatus": {"supported": True},
        "ES.GetStatus": {"supported": False},
        "Foo.Bar": {},
    }
    coordinator.api.get_recent_frames.return_value = [
        {
            "ts": 123456,
            "frame": {"id": 1, "result": "ok"},
            "ip": "192.168.1.100",
            "port": 30000,
        }
    ]

    coordinator.device_model = "Venus A"
    coordinator.firmware_version = 147
    coordinator.update_interval = timedelta(seconds=30)
    coordinator.update_count = 5
    coordinator.data = {
        "device": {
            "device": "Venus A",
            "ver": 147,
            "ble_mac": "AA:BB:CC:DD:EE:FF",
            "wifi_mac": "11:22:33:44:55:66",
            "wifi_name": "MyWifi",
            "ip": "192.168.1.100",
        }
    }

    return coordinator


def test_command_compatibility_summary():
    stats = {
        "A": {"supported": True},
        "B": {"supported": False},
        "C": {},
    }

    result = diagnostics._command_compatibility_summary(stats)

    assert result["supported_commands"] == ["A"]
    assert result["unsupported_commands"] == ["B"]
    assert result["unknown_commands"] == ["C"]
    assert result["support_ratio"] == "1/3"


def test_command_stats_snapshot(coordinator):
    assert diagnostics._command_stats_snapshot(coordinator) == (
        coordinator.api.get_all_command_stats.return_value
    )


def test_command_stats_snapshot_calls_api(coordinator):
    diagnostics._command_stats_snapshot(coordinator)
    coordinator.api.get_all_command_stats.assert_called_once()


def test_coordinator_snapshot_redacts_data(coordinator):
    snapshot = diagnostics._coordinator_snapshot(coordinator)

    assert snapshot["device_model"] == "Venus A"
    assert snapshot["firmware_version"] == 147
    assert snapshot["ble_mac"] == "**REDACTED**"
    assert snapshot["wifi_mac"] == "**REDACTED**"
    assert snapshot["wifi_name"] == "**REDACTED**"
    assert snapshot["device_ip"] == "**REDACTED**"

    assert snapshot["recent_raw_frames"] == [
        {
            "ts": 123456,
            "frame": {"id": 1, "result": "ok"},
        }
    ]


def test_command_compatibility_summary_empty():
    result = diagnostics._command_compatibility_summary({})

    assert result == {
        "supported_commands": [],
        "unsupported_commands": [],
        "unknown_commands": [],
        "support_ratio": "0/0",
    }


def test_coordinator_snapshot_without_frames(coordinator):
    coordinator.api.get_recent_frames.return_value = []

    snapshot = diagnostics._coordinator_snapshot(coordinator)

    assert snapshot["recent_raw_frames"] == []


def test_snapshot_redaction_removes_original_values(coordinator):
    snapshot = diagnostics._coordinator_snapshot(coordinator)

    text = str(snapshot)

    assert "AA:BB:CC:DD:EE:FF" not in text
    assert "11:22:33:44:55:66" not in text
    assert "192.168.1.100" not in text


@pytest.fixture
def multi_coordinator(coordinator):
    """Mock MarstekMultiDeviceCoordinator."""
    multi = diagnostics.MarstekMultiDeviceCoordinator.__new__(
        diagnostics.MarstekMultiDeviceCoordinator
    )

    multi.update_interval = timedelta(seconds=60)
    multi.data = {"aggregates": {"total_power": 1234}}
    multi.device_coordinators = {
        "AA": coordinator,
        "BB": coordinator,
    }

    return multi


def test_multi_diagnostics(multi_coordinator):
    result = diagnostics._multi_diagnostics(multi_coordinator)

    assert result["requested_interval"] == 60
    assert result["aggregates"] == {"total_power": 1234}

    assert len(result["devices"]) == 2
    assert "device_0" in result["devices"]
    assert "device_1" in result["devices"]


def test_multi_diagnostics_without_interval(multi_coordinator):
    multi_coordinator.update_interval = None

    result = diagnostics._multi_diagnostics(multi_coordinator)

    assert result["requested_interval"] is None


def test_multi_diagnostics_without_data(multi_coordinator):
    multi_coordinator.data = None

    result = diagnostics._multi_diagnostics(multi_coordinator)

    assert result["aggregates"] is None


def test_coordinator_snapshot_without_update_interval(coordinator):
    coordinator.update_interval = None

    snapshot = diagnostics._coordinator_snapshot(coordinator)

    assert snapshot["update_interval"] is None


def test_coordinator_snapshot_without_data(coordinator):
    coordinator.data = {}

    snapshot = diagnostics._coordinator_snapshot(coordinator)

    assert snapshot["device_model"] == "Venus A"
    assert snapshot["firmware_version"] == 147


def test_coordinator_snapshot_recent_frame_limit(coordinator):
    coordinator.api.get_recent_frames.return_value = [
        {"ts": i, "frame": {"id": i}, "ip": "1.2.3.4", "port": 30000}
        for i in range(20)
    ]

    snapshot = diagnostics._coordinator_snapshot(coordinator)

    assert len(snapshot["recent_raw_frames"]) == diagnostics.RECENT_FRAMES_LIMIT
    assert snapshot["recent_raw_frames"][0]["ts"] == 12
    assert snapshot["recent_raw_frames"][-1]["ts"] == 19


def test_entity_states_snapshot(monkeypatch):
    registry = MagicMock()

    entity = MagicMock()
    entity.entity_id = "sensor.test"

    state = MagicMock()
    state.state = "42"
    state.attributes = {"unit_of_measurement": "W"}
    state.last_updated.isoformat.return_value = "2026-01-01T00:00:00"

    hass = MagicMock()
    hass.states.get.return_value = state

    monkeypatch.setattr(
        diagnostics.er,
        "async_get",
        lambda hass: registry,
    )

    monkeypatch.setattr(
        diagnostics.er,
        "async_entries_for_config_entry",
        lambda registry, entry_id: [entity],
    )

    result = diagnostics._entity_states_snapshot(hass, "entry")

    assert result["sensor.test"]["state"] == "42"
    assert result["sensor.test"]["unit"] == "W"


def test_entity_states_snapshot_without_state(monkeypatch):
    registry = MagicMock()

    entity = MagicMock()
    entity.entity_id = "sensor.test"

    hass = MagicMock()
    hass.states.get.return_value = None

    monkeypatch.setattr(
        diagnostics.er,
        "async_get",
        lambda _: registry,
    )

    monkeypatch.setattr(
        diagnostics.er,
        "async_entries_for_config_entry",
        lambda *_: [entity],
    )

    result = diagnostics._entity_states_snapshot(hass, "entry")

    assert result["sensor.test"] == {
        "state": None,
        "unit": None,
        "last_updated": None,
    }


def test_entity_states_snapshot_redacted(monkeypatch):
    registry = MagicMock()

    entity = MagicMock()
    entity.entity_id = "sensor.wifi_mac"

    state = MagicMock()
    state.state = "secret"
    state.attributes = {"unit_of_measurement": None}
    state.last_updated.isoformat.return_value = "2026"

    hass = MagicMock()
    hass.states.get.return_value = state

    monkeypatch.setattr(
        diagnostics.er,
        "async_get",
        lambda hass: registry,
    )

    monkeypatch.setattr(
        diagnostics.er,
        "async_entries_for_config_entry",
        lambda registry, entry_id: [entity],
    )

    result = diagnostics._entity_states_snapshot(hass, "entry")

    assert result["sensor.wifi_mac"]["state"] == "**REDACTED**"


def test_entity_states_snapshot_redacted_without_state(monkeypatch):
    registry = MagicMock()

    entity = MagicMock()
    entity.entity_id = "sensor.wifi_mac"

    hass = MagicMock()
    hass.states.get.return_value = None

    monkeypatch.setattr(
        diagnostics.er,
        "async_get",
        lambda _: registry,
    )

    monkeypatch.setattr(
        diagnostics.er,
        "async_entries_for_config_entry",
        lambda *_: [entity],
    )

    result = diagnostics._entity_states_snapshot(hass, "entry")

    assert result["sensor.wifi_mac"] == {
        "state": "**REDACTED**",
        "unit": None,
        "last_updated": None,
    }


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_not_initialized():
    hass = MagicMock()
    hass.data = {}

    entry = MagicMock()
    entry.entry_id = "entry1"

    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

    assert result == {"error": "integration_not_initialized"}


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_single(monkeypatch):
    coordinator = diagnostics.MarstekDataUpdateCoordinator.__new__(
        diagnostics.MarstekDataUpdateCoordinator
    )

    coordinator.api = MagicMock()
    coordinator.api.get_all_command_stats.return_value = {}
    coordinator.api.get_recent_frames.return_value = []
    coordinator.data = {}
    coordinator.update_interval = None
    coordinator.update_count = 0
    coordinator.device_model = "Venus A"
    coordinator.firmware_version = 147

    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            "entry1": {
                DATA_COORDINATOR: coordinator,
            }
        }
    }

    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.title = "Venus A"
    entry.data = {"device": "Venus A"}

    monkeypatch.setattr(
        diagnostics,
        "_entity_states_snapshot",
        lambda *_: {},
    )

    monkeypatch.setattr(
        diagnostics,
        "_coordinator_snapshot",
        lambda *_: {},
    )

    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["title"] == "Venus A"
    assert result["entry"]["device"] == "Venus A"
    assert "device" in result


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_multi(monkeypatch):
    coordinator = diagnostics.MarstekMultiDeviceCoordinator.__new__(
        diagnostics.MarstekMultiDeviceCoordinator
    )

    coordinator.device_coordinators = {
        "AA": object(),
        "BB": object(),
    }
    coordinator.update_interval = None
    coordinator.data = {}

    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            "entry1": {
                DATA_COORDINATOR: coordinator,
            }
        }
    }

    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.title = "Marstek"

    monkeypatch.setattr(
        diagnostics,
        "_entity_states_snapshot",
        lambda *_: {},
    )

    monkeypatch.setattr(
        diagnostics,
        "_multi_diagnostics",
        lambda *_: {"devices": {}, "aggregates": {}},
    )

    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["device_count"] == 2
    assert "multi" in result


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_missing_entry():
    hass = MagicMock()
    hass.data = {
        DOMAIN: {}
    }

    entry = MagicMock()
    entry.entry_id = "missing"

    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

    assert result == {"error": "integration_not_initialized"}


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_unknown(monkeypatch):
    """Unknown coordinator type returns an error."""

    monkeypatch.setattr(
        diagnostics,
        "_entity_states_snapshot",
        lambda *_: {},
    )

    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            "entry1": {
                DATA_COORDINATOR: object(),
            }
        }
    }

    entry = MagicMock()
    entry.entry_id = "entry1"

    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

    assert result == {"error": "unknown_coordinator"}
