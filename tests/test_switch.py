"""Tests for switch.py — Marstek Local API."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import _load_integration_module

# ---------------------------------------------------------------------------
# Load module under test (stubs ensured)
# ---------------------------------------------------------------------------

sys.modules.pop("custom_components.marstek_local_api.switch", None)

_switch_mod = _load_integration_module("switch")

async_setup_entry = _switch_mod.async_setup_entry
MarstekBaseSwitch = _switch_mod.MarstekBaseSwitch
MarstekLedCtrlSwitch = _switch_mod.MarstekLedCtrlSwitch
MarstekBleAdvSwitch = _switch_mod.MarstekBleAdvSwitch
MarstekAPIError = _switch_mod.MarstekAPIError
DOMAIN = _switch_mod.DOMAIN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEVICE_DATA = {
    "ble_mac": "aabbccddeeff",
    "wifi_mac": "112233445566",
    "device": "VenusA",
    "firmware": 147,
}


def _make_entry(**overrides):
    entry = MagicMock()
    entry.data = {**_DEVICE_DATA, **overrides}
    entry.entry_id = "test_entry"
    return entry


def _make_coord():
    coord = MagicMock()
    coord.last_update_success = True
    coord.api = MagicMock()
    coord.api.set_led = AsyncMock(return_value=True)
    coord.api.set_ble_adv = AsyncMock(return_value=True)
    return coord


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------

class TestAsyncSetupEntry:
    async def test_both_features_enabled(self):
        hass = MagicMock()
        entry = _make_entry()
        coord = _make_coord()

        hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}
        add_entities = MagicMock()

        with patch.object(_switch_mod.CompatibilityMatrix, "is_feature_supported", return_value=True):
            await async_setup_entry(hass, entry, add_entities)

        add_entities.assert_called_once()
        entities = add_entities.call_args[0][0]

        assert len(entities) == 2
        assert any(isinstance(e, MarstekLedCtrlSwitch) for e in entities)
        assert any(isinstance(e, MarstekBleAdvSwitch) for e in entities)

    async def test_no_features_enabled(self):
        hass = MagicMock()
        entry = _make_entry()
        coord = _make_coord()

        hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}
        add_entities = MagicMock()

        with patch.object(_switch_mod.CompatibilityMatrix, "is_feature_supported", return_value=False):
            await async_setup_entry(hass, entry, add_entities)

        add_entities.assert_called_once()
        assert add_entities.call_args[0][0] == []


# ---------------------------------------------------------------------------
# Base Switch
# ---------------------------------------------------------------------------

class TestMarstekBaseSwitch:
    def test_unique_id_fallback_wifi(self):
        coord = _make_coord()
        entry = _make_entry(ble_mac=None)

        sw = MarstekBaseSwitch(coord, entry)
        assert "112233445566" in sw._attr_unique_id

    def test_available_true(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())
        assert sw.available is True

    def test_available_false(self):
        coord = _make_coord()
        coord.last_update_success = False
        sw = MarstekBaseSwitch(coord, _make_entry())
        assert sw.available is False

    async def test_restore_state(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        fake_state = MagicMock()
        fake_state.state = "on"

        with patch.object(sw, "async_get_last_state", return_value=fake_state):
            await sw.async_added_to_hass()

        assert sw._state is True

    def test_safe_write_state_no_entity_id(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        sw.entity_id = None
        sw._safe_write_state()  # should not crash


# ---------------------------------------------------------------------------
# LED Switch
# ---------------------------------------------------------------------------

class TestMarstekLedCtrlSwitch:
    def test_turn_on_success(self):
        coord = _make_coord()
        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write_mock:
            import asyncio
            asyncio.run(sw.async_turn_on())

        assert sw._state is True
        write_mock.assert_called_once()

    def test_turn_off_success(self):
        coord = _make_coord()
        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write_mock:
            import asyncio
            asyncio.run(sw.async_turn_off())

        assert sw._state is False
        write_mock.assert_called_once()

    def test_api_exception(self):
        coord = _make_coord()
        coord.api.set_led = AsyncMock(side_effect=MarstekAPIError("fail"))

        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        import asyncio
        asyncio.run(sw.async_turn_on())

        assert sw._state is True  # unchanged default


# ---------------------------------------------------------------------------
# BLE Switch
# ---------------------------------------------------------------------------

class TestMarstekBleAdvSwitch:
    def test_turn_on_success(self):
        coord = _make_coord()
        sw = MarstekBleAdvSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write_mock:
            import asyncio
            asyncio.run(sw.async_turn_on())

        assert sw._state is True
        write_mock.assert_called_once()

    def test_turn_off_success(self):
        coord = _make_coord()
        sw = MarstekBleAdvSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write_mock:
            import asyncio
            asyncio.run(sw.async_turn_off())

        assert sw._state is False
        write_mock.assert_called_once()

    def test_ble_exception(self):
        coord = _make_coord()
        coord.api.set_ble_adv = AsyncMock(side_effect=MarstekAPIError("fail"))

        sw = MarstekBleAdvSwitch(coord, _make_entry())

        import asyncio
        asyncio.run(sw.async_turn_on())

        assert sw._state is True
