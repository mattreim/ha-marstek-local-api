"""Tests for binary sensor value functions using Venus A FW 147 fixture data."""
import pytest

from unittest.mock import MagicMock

from custom_components.marstek_local_api.binary_sensor import (
    async_setup_entry,
    BINARY_SENSOR_TYPES,
    MarstekBinarySensor,
    MarstekBinarySensorEntityDescription,
    MarstekMultiDeviceBinarySensor,
    MarstekMultiDeviceCoordinator,
)
from custom_components.marstek_local_api.const import (
    DOMAIN,
    DATA_COORDINATOR,
)


@pytest.fixture
def coordinator():
    coordinator = MagicMock()
    coordinator.data = {"battery": {"charg_flag": True}}
    coordinator.is_category_fresh.return_value = True
    return coordinator


@pytest.fixture
def entry():
    entry = MagicMock()
    entry.data = {
        "ble_mac": "AA:BB:CC:DD:EE:FF",
        "device": "Venus A",
        "firmware": 147,
    }
    return entry


class FakeMultiCoordinator(MarstekMultiDeviceCoordinator):
    pass


class TestBinarySensorsVenusA:
    """Verify binary sensor value_fn with real fixture data."""

    def test_charging_enabled_true(self, binary_sensor_map, venus_a_coordinator_data):
        """charg_flag=True → charging_enabled is on."""
        val = binary_sensor_map["charging_enabled"].value_fn(venus_a_coordinator_data)
        assert val is True

    def test_discharging_enabled_true(self, binary_sensor_map, venus_a_coordinator_data):
        """dischrg_flag=True → discharging_enabled is on."""
        val = binary_sensor_map["discharging_enabled"].value_fn(venus_a_coordinator_data)
        assert val is True

    def test_bluetooth_connected_true(self, binary_sensor_map, venus_a_coordinator_data):
        """BLE state='connect' → bluetooth_connected is on."""
        val = binary_sensor_map["bluetooth_connected"].value_fn(venus_a_coordinator_data)
        assert val is True

    def test_ct_connected_true(self, binary_sensor_map, venus_a_coordinator_data):
        """ct_state=1 → ct_connected is on."""
        val = binary_sensor_map["ct_connected"].value_fn(venus_a_coordinator_data)
        assert val is True


class TestBinarySensorsEdgeCases:
    """Verify binary sensor value_fn with synthetic data covering off states."""

    def test_charging_disabled(self, binary_sensor_map):
        data = {"battery": {"charg_flag": False, "dischrg_flag": True}}
        assert binary_sensor_map["charging_enabled"].value_fn(data) is False

    def test_discharging_disabled(self, binary_sensor_map):
        data = {"battery": {"charg_flag": True, "dischrg_flag": False}}
        assert binary_sensor_map["discharging_enabled"].value_fn(data) is False

    def test_bluetooth_disconnected(self, binary_sensor_map):
        data = {"ble": {"state": "disconnect", "ble_mac": "aabbccddeeff"}}
        assert binary_sensor_map["bluetooth_connected"].value_fn(data) is False

    def test_ct_disconnected(self, binary_sensor_map):
        data = {"em": {"ct_state": 0, "a_power": 0, "total_power": 0}}
        assert binary_sensor_map["ct_connected"].value_fn(data) is False

    def test_charging_absent_defaults_false(self, binary_sensor_map):
        """Missing battery key → default False."""
        assert binary_sensor_map["charging_enabled"].value_fn({}) is False

    def test_discharging_absent_defaults_false(self, binary_sensor_map):
        assert binary_sensor_map["discharging_enabled"].value_fn({}) is False

    def test_bluetooth_absent_is_false(self, binary_sensor_map):
        """Missing ble key → state is None, not 'connect' → False."""
        assert binary_sensor_map["bluetooth_connected"].value_fn({}) is False

    def test_ct_absent_is_false(self, binary_sensor_map):
        """Missing em key → ct_state is None, not 1 → False."""
        assert binary_sensor_map["ct_connected"].value_fn({}) is False

    def test_bluetooth_unknown_state(self, binary_sensor_map):
        """Unknown BLE state string → not 'connect' → False."""
        data = {"ble": {"state": "connecting"}}
        assert binary_sensor_map["bluetooth_connected"].value_fn(data) is False

    @pytest.mark.parametrize(
        ("device_data", "expected_name", "expected_model"),
        [
           (
                {"device": "Venus A", "firmware": 147},
                "Marstek Venus A EEFF",
                "Venus A",
            ),
            (
                {},
                "Marstek Device EEFF",
                "Unknown",
            ),
        ],
    )
    def test_device_info(self, coordinator, device_data, expected_name, expected_model):
        multi = MagicMock()

        entity = MarstekMultiDeviceBinarySensor(
            coordinator=multi,
            device_coordinator=coordinator,
            entity_description=BINARY_SENSOR_TYPES[0],
            device_mac="AA:BB:CC:DD:EE:FF",
            device_data=device_data,
        )

        assert entity._attr_device_info["name"] == expected_name
        assert entity._attr_device_info["model"] == expected_model


class TestMarstekBinarySensor:

    @pytest.mark.asyncio
    async def test_async_setup_entry_single_device(self, coordinator, entry):
        coordinator = MagicMock()

        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                "entry_id": {
                    DATA_COORDINATOR: coordinator,
                }
            }
        }

        entry = MagicMock()
        entry.entry_id = "entry_id"
        entry.data = {
            "ble_mac": "AA",
            "device": "Venus A",
            "firmware": 147,
        }

        add_entities = MagicMock()

        await async_setup_entry(
            hass,
            entry,
            add_entities,
        )

        entities = add_entities.call_args.args[0]

        assert len(entities) == len(BINARY_SENSOR_TYPES)

    def test_is_on_true(self, coordinator, entry):
        description = MarstekBinarySensorEntityDescription(
            key="charging_enabled",
            value_fn=lambda d: True,
            category="battery",
        )

        entity = MarstekBinarySensor(
            coordinator,
            description,
            entry,
        )

        assert entity.is_on is True

    def test_is_on_stale_returns_none(self, coordinator, entry):
        coordinator.is_category_fresh.return_value = False

        description = MarstekBinarySensorEntityDescription(
            key="charging_enabled",
            value_fn=lambda d: True,
            category="battery",
        )

        entity = MarstekBinarySensor(
            coordinator,
            description,
            entry,
        )

        assert entity.is_on is None

    def test_is_on_without_value_fn_but_category(self, coordinator, entry):
        description = MarstekBinarySensorEntityDescription(
            key="dummy",
            category="battery",
        )

        entity = MarstekBinarySensor(
            coordinator,
            description,
            entry,
        )

        assert entity.is_on is None

    def test_available_with_data(self, coordinator, entry):
        description = MarstekBinarySensorEntityDescription(
            key="charging_enabled",
            value_fn=lambda d: True,
        )

        entity = MarstekBinarySensor(
            coordinator,
            description,
            entry,
        )

        assert entity.available is True

    def test_available_without_data(self, coordinator, entry):
        coordinator.data = {}

        description = MarstekBinarySensorEntityDescription(
            key="charging_enabled",
            value_fn=lambda d: True,
        )

        entity = MarstekBinarySensor(
            coordinator,
            description,
            entry,
        )

        assert entity.available is False

    def test_available_fn_used(self, coordinator, entry):
        description = MarstekBinarySensorEntityDescription(
            key="charging_enabled",
            value_fn=lambda d: True,
            available_fn=lambda d: False,
        )

        entity = MarstekBinarySensor(
            coordinator,
            description,
            entry,
        )

        assert entity.available is False

    def test_available_fn_true(self, coordinator, entry):
        description = MarstekBinarySensorEntityDescription(
            key="charging_enabled",
            available_fn=lambda _: True,
        )

        entity = MarstekBinarySensor(
            coordinator,
            description,
            entry,
        )

        assert entity.available is True

    def test_unique_id_and_device_info(self, coordinator, entry):
        entity = MarstekBinarySensor(
            coordinator,
            BINARY_SENSOR_TYPES[0],
            entry,
        )

        assert entity._attr_unique_id == "AA:BB:CC:DD:EE:FF_charging_enabled"

        assert entity._attr_device_info["model"] == "Venus A"
        assert entity._attr_device_info["sw_version"] == "147"
        assert entity._attr_device_info["identifiers"] == {
            ("marstek_local_api", "AA:BB:CC:DD:EE:FF")
        }

    def test_unique_id_uses_wifi_mac(self, coordinator, entry):
        """Fallback to wifi_mac when ble_mac is unavailable."""
        entry.data.pop("ble_mac")
        entry.data["wifi_mac"] = "11:22:33:44:55:66"

        entity = MarstekBinarySensor(
            coordinator,
            BINARY_SENSOR_TYPES[0],
            entry,
        )

        assert entity._attr_unique_id == "11:22:33:44:55:66_charging_enabled"


class TestMarstekMultiDeviceBinarySensor:

    @pytest.mark.asyncio
    async def test_async_setup_entry_multi_device(self, coordinator, entry, monkeypatch):
        coordinator = FakeMultiCoordinator.__new__(FakeMultiCoordinator)

        coordinator.device_coordinators = {
            "AA": MagicMock(),
        }

        coordinator.devices = [
            {
                "ble_mac": "AA",
                "device": "Venus A",
                "firmware": 147,
            }
        ]

        coordinator.get_device_macs = MagicMock(return_value=["AA"])

        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                "entry_id": {
                    DATA_COORDINATOR: coordinator,
                }
            }
        }

        entry = MagicMock()
        entry.entry_id = "entry_id"

        add_entities = MagicMock()

        await async_setup_entry(
            hass,
            entry,
            add_entities,
        )

        entities = add_entities.call_args.args[0]

        assert len(entities) == len(BINARY_SENSOR_TYPES)

    def test_is_on(self, coordinator):
        multi = MagicMock()
        multi.get_device_data.return_value = {
            "battery": {"charg_flag": True},
        }

        entity = MarstekMultiDeviceBinarySensor(
            coordinator=multi,
            device_coordinator=coordinator,
            entity_description=BINARY_SENSOR_TYPES[0],
            device_mac="AA",
            device_data={},
        )

        assert entity.is_on is True

    def test_is_on_stale_returns_none(self, coordinator):
        coordinator.is_category_fresh.return_value = False

        multi = MagicMock()
        multi.get_device_data.return_value = {
            "battery": {"charg_flag": True},
        }

        entity = MarstekMultiDeviceBinarySensor(
            coordinator=multi,
            device_coordinator=coordinator,
            entity_description=BINARY_SENSOR_TYPES[0],
            device_mac="AA",
            device_data={},
        )

        assert entity.is_on is None

    def test_is_on_without_value_fn(self, coordinator):
        multi = MagicMock()

        entity = MarstekMultiDeviceBinarySensor(
            coordinator=multi,
            device_coordinator=coordinator,
            entity_description=MarstekBinarySensorEntityDescription(
                key="dummy",
                category="battery",
            ),
            device_mac="AA",
            device_data={},
        )

        assert entity.is_on is None

    def test_available(self, coordinator):
        multi = MagicMock()
        multi.get_device_data.return_value = {"battery": {}}

        entity = MarstekMultiDeviceBinarySensor(
            coordinator=multi,
            device_coordinator=coordinator,
            entity_description=MarstekBinarySensorEntityDescription(
                key="charging_enabled",
                value_fn=lambda d: True,
            ),
            device_mac="AA",
            device_data={},
        )

        assert entity.available is True

    def test_available_without_data(self, coordinator):
        multi = MagicMock()
        multi.get_device_data.return_value = {}

        entity = MarstekMultiDeviceBinarySensor(
            coordinator=multi,
            device_coordinator=coordinator,
            entity_description=MarstekBinarySensorEntityDescription(
                key="charging_enabled",
                value_fn=lambda d: True,
            ),
            device_mac="AA",
            device_data={},
        )

        assert entity.available is False

    def test_available_fn(self, coordinator):
        multi = MagicMock()
        multi.get_device_data.return_value = {}

        entity = MarstekMultiDeviceBinarySensor(
            coordinator=multi,
            device_coordinator=coordinator,
            entity_description=MarstekBinarySensorEntityDescription(
                key="charging_enabled",
                value_fn=lambda d: True,
                available_fn=lambda d: False,
            ),
            device_mac="AA",
            device_data={},
        )

        assert entity.available is False

    def test_available_fn_true(self, coordinator):
        multi = MagicMock()
        multi.get_device_data.return_value = {}

        entity = MarstekMultiDeviceBinarySensor(
            coordinator=multi,
            device_coordinator=coordinator,
            entity_description=MarstekBinarySensorEntityDescription(
                key="charging_enabled",
                available_fn=lambda _: True,
            ),
            device_mac="AA",
            device_data={},
        )

        assert entity.available is True
