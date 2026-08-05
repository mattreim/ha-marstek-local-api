"""Switch platform for Marstek Local API."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .api import MarstekAPIError
from .compatibility import CompatibilityMatrix
from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import MarstekDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    device_compatibility = CompatibilityMatrix(
        entry.data.get("device", ""),
        entry.data.get("firmware", 0),
    )

    entities = []

    if device_compatibility.is_feature_supported("led_control"):
        entities.append(MarstekLedCtrlSwitch(coordinator, entry))
    else:
        _LOGGER.debug(
            "LED control not supported for %s FW %d",
            device_compatibility.base_model,
            device_compatibility.firmware_version,
        )

    if device_compatibility.is_feature_supported("ble_adv"):
        entities.append(MarstekBleAdvSwitch(coordinator, entry))
    else:
        _LOGGER.debug(
            "Bluetooth lock not supported for %s FW %d",
            device_compatibility.base_model,
            device_compatibility.firmware_version,
        )

    async_add_entities(entities)


class MarstekBaseSwitch(CoordinatorEntity, RestoreEntity, SwitchEntity):
    """Base switch entity."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    default_state = True

    def _safe_write_state(self) -> None:
        if self.entity_id is None:
            return
        self.async_write_ha_state()

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)

        device_id = entry.data.get("ble_mac") or entry.data.get("wifi_mac")
        self._attr_unique_id = f"{device_id}_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"Marstek {entry.data.get('device', 'Unknown')}",
            manufacturer="Marstek",
            model=entry.data.get("device", "Unknown"),
            sw_version=str(entry.data.get("firmware", "Unknown")),
        )

        self._state = self.default_state

    @property
    def is_on(self) -> bool:
        """Return if the switch is on."""
        return self._state

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return bool(self.coordinator.last_update_success)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._state = last_state.state == "on"


class MarstekLedCtrlSwitch(MarstekBaseSwitch):
    """LED control switch."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)

        device_id = entry.data.get("ble_mac") or entry.data.get("wifi_mac")
        self._attr_unique_id = f"{device_id}_led_ctrl"
        self._attr_name = "Status LED"

    async def async_turn_on(self, **_kwargs) -> None:
        try:
            success = await self.coordinator.api.set_led(True)
        except MarstekAPIError as err:
            _LOGGER.warning("LED control not supported: %s", err)
            return

        if success:
            self._state = True
            self._safe_write_state()

    async def async_turn_off(self, **_kwargs) -> None:
        try:
            success = await self.coordinator.api.set_led(False)
        except MarstekAPIError as err:
            _LOGGER.warning("LED control not supported: %s", err)
            return

        if success:
            self._state = False
            self._safe_write_state()


class MarstekBleAdvSwitch(MarstekBaseSwitch):
    """Bluetooth lock switch."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)

        device_id = entry.data.get("ble_mac") or entry.data.get("wifi_mac")
        self._attr_unique_id = f"{device_id}_ble_adv"
        self._attr_name = "Bluetooth lock"

    async def async_turn_on(self, **_kwargs) -> None:
        try:
            success = await self.coordinator.api.set_ble_adv(True)
        except MarstekAPIError as err:
            _LOGGER.warning("Bluetooth lock not supported: %s", err)
            return

        if success:
            self._state = True
            self._safe_write_state()

    async def async_turn_off(self, **_kwargs) -> None:
        try:
            success = await self.coordinator.api.set_ble_adv(False)
        except MarstekAPIError as err:
            _LOGGER.warning("Bluetooth lock not supported: %s", err)
            return

        if success:
            self._state = False
            self._safe_write_state()
