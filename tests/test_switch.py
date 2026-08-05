"""Tests for switch.py — Marstek Local API."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from types import SimpleNamespace

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
    return SimpleNamespace(
        data={**_DEVICE_DATA, **overrides},
        entry_id="test_entry",
    )


def _make_coord():
    coord = MagicMock()
    coord.last_update_success = True
    coord.api = MagicMock()
    coord.api.set_led = AsyncMock(return_value=True)
    coord.api.set_ble_adv = AsyncMock(return_value=True)
    coord.data = {}
    coord.device_model = "VenusA"
    coord.firmware_version = 147
    return coord


# ---------------------------------------------------------------------------
# Device Info
# ---------------------------------------------------------------------------

def test_device_info_defaults():
    coord = _make_coord()

    entry = SimpleNamespace(
        data={},
        entry_id="1",
    )

    sw = MarstekBaseSwitch(coord, entry)

    assert sw._attr_device_info["model"] == "Unknown"
    assert sw._attr_device_info["name"] == "Marstek Unknown"


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------

class TestAsyncSetupEntry:

    @pytest.mark.asyncio
    async def test_only_led_supported(self):
        hass = MagicMock()
        coord = _make_coord()
        entry = _make_entry()

        hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}

        add = MagicMock()

        with patch.object(
            _switch_mod.CompatibilityMatrix,
            "is_feature_supported",
            side_effect=lambda feature: feature == "led_control",
        ):
            await async_setup_entry(hass, entry, add)

        entities = add.call_args[0][0]

        assert len(entities) == 1
        assert isinstance(entities[0], MarstekLedCtrlSwitch)

    @pytest.mark.asyncio
    async def test_only_ble_supported(self):
        hass = MagicMock()
        coord = _make_coord()
        entry = _make_entry()

        hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}

        add = MagicMock()

        with patch.object(
            _switch_mod.CompatibilityMatrix,
            "is_feature_supported",
            side_effect=lambda feature: feature == "ble_adv",
        ):
            await async_setup_entry(hass, entry, add)

        entities = add.call_args[0][0]

        assert len(entities) == 1
        assert isinstance(entities[0], MarstekBleAdvSwitch)

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_setup_entry_missing_coordinator(self):
        hass = MagicMock()
        entry = _make_entry()

        hass.data = {}

        with pytest.raises(KeyError):
            await async_setup_entry(
                hass,
                entry,
                MagicMock(),
            )


# ---------------------------------------------------------------------------
# Base Switch
# ---------------------------------------------------------------------------

class TestMarstekBaseSwitch:

    def test_default_state(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        assert sw.is_on is True

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

    @pytest.mark.asyncio
    async def test_restore_state(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        state = MagicMock()
        state.state = "on"

        with patch.object(sw, "async_get_last_state", return_value=state):
            await sw.async_added_to_hass()

        assert sw.is_on is True

    @pytest.mark.asyncio
    async def test_restore_state_none(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        with patch.object(sw, "async_get_last_state", return_value=None):
            await sw.async_added_to_hass()

        assert sw._state is True

    @pytest.mark.asyncio
    async def test_restore_state_invalid(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        state = MagicMock()
        state.state = "unknown"

        with patch.object(sw, "async_get_last_state", return_value=state):
            await sw.async_added_to_hass()

        assert sw.is_on is False

    @pytest.mark.asyncio
    async def test_restore_state_off(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        state = MagicMock()
        state.state = "off"

        with patch.object(sw, "async_get_last_state", return_value=state):
            await sw.async_added_to_hass()

        assert sw.is_on is False

    def test_safe_write_state_no_entity_id(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        sw.entity_id = None
        sw._safe_write_state()  # should not crash

    def test_safe_write_state_calls_async_write(self):
        coord = _make_coord()
        sw = MarstekBaseSwitch(coord, _make_entry())

        sw.entity_id = "switch.test"
        sw.async_write_ha_state = MagicMock()

        sw._safe_write_state()

        sw.async_write_ha_state.assert_called_once()

    def test_safe_write_state_without_entity_id(self):
        sw = MarstekBaseSwitch(_make_coord(), _make_entry())
        sw.entity_id = None

        sw._safe_write_state()


# ---------------------------------------------------------------------------
# LED Switch
# ---------------------------------------------------------------------------

class TestMarstekLedCtrlSwitch:

    @pytest.mark.asyncio
    async def test_led_turn_on_success(self):
        coord = _make_coord()
        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write_mock:
            await sw.async_turn_on()

        assert sw._state is True
        write_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_led_turn_on_returns_false(self):
        coord = _make_coord()
        coord.api.set_led.return_value = False

        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write:
            await sw.async_turn_on()

        write.assert_not_called()
        assert sw._state is True

    @pytest.mark.asyncio
    async def test_led_turn_on_exception_logs(self, caplog):
        coord = _make_coord()
        coord.api.set_led.side_effect = MarstekAPIError("failed")

        sw = MarstekLedCtrlSwitch(
            coord,
            _make_entry(),
        )

        await sw.async_turn_on()

        assert "LED control not supported" in caplog.text
        assert sw.is_on is True

    @pytest.mark.asyncio
    async def test_led_turn_off_success(self):
        coord = _make_coord()
        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write_mock:
            await sw.async_turn_off()

        assert sw._state is False
        write_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_led_turn_off_returns_false(self):
        coord = _make_coord()
        coord.api.set_led.return_value = False

        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write:
            await sw.async_turn_off()

        write.assert_not_called()
        assert sw._state is True

    @pytest.mark.asyncio
    async def test_led_turn_off_exception(self, caplog):
        coord = _make_coord()
        coord.api.set_led = AsyncMock(side_effect=MarstekAPIError("boom"))

        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        await sw.async_turn_off()

        assert "LED control not supported" in caplog.text
        assert sw.is_on is True

    @pytest.mark.asyncio
    async def test_led_api_exception(self):
        coord = _make_coord()
        coord.api.set_led = AsyncMock(side_effect=MarstekAPIError("fail"))

        sw = MarstekLedCtrlSwitch(coord, _make_entry())

        await sw.async_turn_on()

        assert sw._state is True  # unchanged default

    def test_led_name(self):
        sw = MarstekLedCtrlSwitch(
            _make_coord(),
            _make_entry(),
        )

        assert sw._attr_name == "Status LED"


# ---------------------------------------------------------------------------
# BLE Switch
# ---------------------------------------------------------------------------

class TestMarstekBleAdvSwitch:

    @pytest.mark.asyncio
    async def test_ble_turn_on_success(self):
        coord = _make_coord()
        sw = MarstekBleAdvSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write_mock:
            await sw.async_turn_on()

        assert sw._state is True
        write_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_ble_turn_on_returns_false(self):
        coord = _make_coord()
        coord.api.set_ble_adv.return_value = False

        sw = MarstekBleAdvSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write:
            await sw.async_turn_on()

        write.assert_not_called()

    @pytest.mark.asyncio
    async def test_ble_turn_off_success(self):
        coord = _make_coord()
        sw = MarstekBleAdvSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write_mock:
            await sw.async_turn_off()

        assert sw._state is False
        write_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_ble_turn_off_returns_false(self):
        coord = _make_coord()
        coord.api.set_ble_adv.return_value = False

        sw = MarstekBleAdvSwitch(coord, _make_entry())

        with patch.object(sw, "_safe_write_state") as write:
            await sw.async_turn_off()

        write.assert_not_called()

    @pytest.mark.asyncio
    async def test_ble_turn_off_exception(self, caplog):
        coord = _make_coord()
        coord.api.set_ble_adv = AsyncMock(side_effect=MarstekAPIError("boom"))

        sw = MarstekBleAdvSwitch(coord, _make_entry())

        await sw.async_turn_off()

        assert "Bluetooth lock not supported" in caplog.text
        assert sw.is_on is True

    @pytest.mark.asyncio
    async def test_ble_exception(self):
        coord = _make_coord()
        coord.api.set_ble_adv = AsyncMock(side_effect=MarstekAPIError("fail"))

        sw = MarstekBleAdvSwitch(coord, _make_entry())

        await sw.async_turn_on()

        assert sw._state is True

    def test_ble_name(self):
        sw = MarstekBleAdvSwitch(
            _make_coord(),
            _make_entry(),
        )

        assert sw._attr_name == "Bluetooth lock"
