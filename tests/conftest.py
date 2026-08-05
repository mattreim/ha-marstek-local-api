"""Shared pytest fixtures and HA module mocks for Marstek integration tests."""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_PATH = REPO_ROOT / "custom_components" / "marstek_local_api"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# Minimal Home Assistant module stubs
# (mirrors the approach in test/test_tool.py)
# ---------------------------------------------------------------------------

def _make_module(name: str, **attrs):
    mod = type(sys)(name)
    mod.__dict__.update(attrs)
    return mod


class _SensorDeviceClass:
    BATTERY = "battery"
    TEMPERATURE = "temperature"
    ENERGY_STORAGE = "energy_storage"
    POWER = "power"
    ENERGY = "energy"
    SIGNAL_STRENGTH = "signal_strength"
    DURATION = "duration"
    VOLTAGE = "voltage"
    CURRENT = "current"


class _SensorStateClass:
    MEASUREMENT = "measurement"
    TOTAL_INCREASING = "total_increasing"


class _BinarySensorDeviceClass:
    BATTERY_CHARGING = "battery_charging"
    CONNECTIVITY = "connectivity"


@dataclass
class _SensorEntityDescription:
    """Minimal HA SensorEntityDescription stub."""
    key: str
    name: str | None = None
    native_unit_of_measurement: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    entity_category: str | None = None


@dataclass
class _BinarySensorEntityDescription:
    key: str
    name: str | None = None
    device_class: str | None = None


class _UnitOfEnergy:
    WATT_HOUR = "Wh"
    KILO_WATT_HOUR = "kWh"


class _UnitOfPower:
    WATT = "W"


class _UnitOfTemperature:
    CELSIUS = "°C"


class _UnitOfElectricPotential:
    VOLT = "V"


class _UnitOfElectricCurrent:
    AMPERE = "A"


class _UnitOfTime:
    SECONDS = "s"


class _DataUpdateCoordinator:
    """Stub base class for coordinators."""
    def __init__(self, *args, **kwargs):
        if args:
            self.hass = args[0]

        self.update_interval = kwargs.get("update_interval")
        self.data = None
        self.last_update_success = True


class _CoordinatorEntity:
    """Minimal HA CoordinatorEntity stub."""
    def __init__(self, coordinator=None, *args, **kwargs):
        self.coordinator = coordinator
        super_init = getattr(super(), "__init__", None)
        if super_init:
            super_init()


class _SensorEntity:
    """Stub sensor entity base."""


class _BinarySensorEntity:
    """Stub binary sensor entity base."""


class _ButtonEntity:
    """Stub button entity base."""


class _ConfigFlowBase:
    """Stub base class for config flows."""
    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(self):
        self.context = {}

        self.hass = SimpleNamespace(
            data={},
            config_entries=SimpleNamespace(
                async_update_entry=AsyncMock(),
            ),
        )

    async def async_show_form(self, **kwargs):
        return {
            "type": "form",
            **kwargs,
        }

    async def async_create_entry(self, *, title, data):
        return {
            "type": "create_entry",
            "title": title,
            "data": data,
        }

    async def async_abort(self, *, reason):
        return {
            "type": "abort",
            "reason": reason,
        }

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self, updates=None):
        return None

    def _async_current_entries(self):
        return []


class _ConfigEntry:
    def __init__(
        self,
        *,
        entry_id="test",
        data=None,
        options=None,
        title="Marstek",
    ):
        self.entry_id = entry_id
        self.data = data or {}
        self.options = options or {}
        self.title = title


class _OptionsFlowBase:
    def __init__(self, config_entry=None):
        self._config_entry = config_entry
        self.hass = SimpleNamespace(
            data={},
            config_entries=SimpleNamespace(
                async_update_entry=AsyncMock(),
            ),
        )

    async def async_show_form(self, **kwargs):
        return {
            "type": "form",
            **kwargs,
        }

    async def async_create_entry(self, *, title, data):
        return {
            "type": "create_entry",
            "title": title,
            "data": data,
        }

    async def async_abort(self, *, reason):
        return {
            "type": "abort",
            "reason": reason,
        }


class _DeviceInfo(dict):
    """Minimal DeviceInfo stub."""


class _DhcpServiceInfo:
    def __init__(self, ip: str, hostname: str = "", macaddress: str = ""):
        self.ip = ip
        self.hostname = hostname
        self.macaddress = macaddress


class _HomeAssistantError(Exception):
    """Stub for Home Assistant base exception."""


def _install_ha_stubs() -> None:
    """Register minimal HA stubs so integration modules can be imported."""
    stubs = {
        "homeassistant": ModuleType("homeassistant"),
        "homeassistant.core": _make_module("core", HomeAssistant=object),
        "homeassistant.helpers": type(sys)("homeassistant.helpers"),
        "homeassistant.helpers.update_coordinator": _make_module(
            "helpers.update_coordinator",
            DataUpdateCoordinator=_DataUpdateCoordinator,
            UpdateFailed=Exception,
            CoordinatorEntity=_CoordinatorEntity,
        ),
        "homeassistant.helpers.entity": _make_module("helpers.entity", DeviceInfo=_DeviceInfo),
        "homeassistant.helpers.entity_platform": _make_module(
            "helpers.entity_platform", AddEntitiesCallback=object
        ),
        "homeassistant.helpers.config_validation": _make_module(
            "helpers.config_validation",
            string=lambda x: x,
            time=lambda x: x,
            boolean=lambda x: x,
            ensure_list=lambda x: x if isinstance(x, list) else [x],
        ),
        "homeassistant.helpers.device_registry": _make_module("helpers.device_registry"),
        "homeassistant.helpers.selector": _make_module(
            "helpers.selector",
            NumberSelector=lambda *a, **kw: None,
            NumberSelectorConfig=lambda *a, **kw: None,
            NumberSelectorMode=SimpleNamespace(BOX="box"),
        ),
        "homeassistant.config_entries": _make_module(
            "config_entries",
            ConfigEntry=_ConfigEntry,
            ConfigFlow=_ConfigFlowBase,
            OptionsFlow=_OptionsFlowBase,
        ),
        "homeassistant.data_entry_flow": _make_module("data_entry_flow", FlowResult=dict),
        "homeassistant.exceptions": _make_module("exceptions", HomeAssistantError=_HomeAssistantError),
        "homeassistant.components": type(sys)("homeassistant.components"),
        "homeassistant.components.dhcp": _make_module("components.dhcp", DhcpServiceInfo=_DhcpServiceInfo),
        "homeassistant.components.sensor": _make_module(
            "components.sensor",
            SensorDeviceClass=_SensorDeviceClass,
            SensorEntity=_SensorEntity,
            SensorEntityDescription=_SensorEntityDescription,
            SensorStateClass=_SensorStateClass,
        ),
        "homeassistant.components.button": _make_module(
            "components.button",
            ButtonEntity=_ButtonEntity,
        ),
        "homeassistant.components.binary_sensor": _make_module(
            "components.binary_sensor",
            BinarySensorDeviceClass=_BinarySensorDeviceClass,
            BinarySensorEntity=_BinarySensorEntity,
            BinarySensorEntityDescription=_BinarySensorEntityDescription,
        ),
        "homeassistant.const": _make_module(
            "const",
            CONF_HOST="host",
            PERCENTAGE="%",
            Platform=SimpleNamespace(
                SENSOR="sensor",
                BINARY_SENSOR="binary_sensor",
                BUTTON="button",
                SWITCH="switch",
            ),
            UnitOfEnergy=_UnitOfEnergy(),
            UnitOfPower=_UnitOfPower(),
            UnitOfTemperature=_UnitOfTemperature(),
            UnitOfElectricPotential=_UnitOfElectricPotential(),
            UnitOfElectricCurrent=_UnitOfElectricCurrent(),
            UnitOfTime=_UnitOfTime(),
        ),
        "voluptuous": _make_module(
            "voluptuous",
            Schema=lambda x=None, **kw: x,
            Required=lambda x: x,
            Optional=lambda x, **kw: x,
            All=lambda *a: a[0],
            Coerce=lambda t: t,
            Range=lambda **kw: None,
            In=lambda x: x,
        ),
    }
    # Modules that must always be replaced — the real HA versions have property
    # machinery (deprecation guards, metaclasses) that break unit tests.
    ALWAYS_REPLACE = {"homeassistant.config_entries"}

    for name, mod in stubs.items():
        if name not in sys.modules or name in ALWAYS_REPLACE:
            sys.modules[name] = mod


# Install stubs once at import time
_install_ha_stubs()


# ---------------------------------------------------------------------------
# Load integration modules
# ---------------------------------------------------------------------------

def _load_integration_module(name: str) -> ModuleType:
    package = "custom_components.marstek_local_api"

    # Ensure package stubs exist
    if "custom_components" not in sys.modules:
        pkg = ModuleType("custom_components")
        pkg.__path__ = [str(INTEGRATION_PATH.parent)]
        sys.modules["custom_components"] = pkg
    if package not in sys.modules:
        pkg = ModuleType(package)
        pkg.__path__ = [str(INTEGRATION_PATH)]
        sys.modules[package] = pkg

        # Make subpackage accessible as attribute of parent package
        sys.modules["custom_components"].marstek_local_api = pkg

    full_name = f"{package}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]

    spec = importlib.util.spec_from_file_location(full_name, INTEGRATION_PATH / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)

    # Allow monkeypatch/import resolution:
    setattr(sys.modules[package], name, mod)
    return mod


# Pre-load in dependency order
_const = _load_integration_module("const")
_compatibility = _load_integration_module("compatibility")
_sensor = _load_integration_module("sensor")
_binary_sensor = _load_integration_module("binary_sensor")


# ---------------------------------------------------------------------------
# Public re-exports for tests
# ---------------------------------------------------------------------------

CompatibilityMatrix = _compatibility.CompatibilityMatrix
SENSOR_TYPES = _sensor.SENSOR_TYPES
PV_SENSOR_TYPES = _sensor.PV_SENSOR_TYPES
BINARY_SENSOR_TYPES = _binary_sensor.BINARY_SENSOR_TYPES


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def venus_a_fw147_raw() -> dict:
    """Raw fixture data as captured from the Venus A FW 147 device."""
    path = FIXTURES_DIR / "Venus_A_fw147" / "all.json"
    data = json.loads(path.read_text())
    return {k: v for k, v in data.items() if not k.startswith("_")}


@pytest.fixture(scope="session")
def venus_a_compatibility() -> CompatibilityMatrix:
    """CompatibilityMatrix for Venus A hardware 2.0, firmware 147."""
    return CompatibilityMatrix(device_model="VenusA", firmware_version=147)


@pytest.fixture(scope="session")
def venus_a_coordinator_data(venus_a_fw147_raw, venus_a_compatibility) -> dict:
    """Simulate coordinator data after scaling is applied, matching real device output.

    Applies the same scaling the coordinator does in _async_update_data().
    ES data is absent in this fixture (ES.GetStatus not captured), so battery
    power sensors will report 0 / idle.
    """
    raw = venus_a_fw147_raw

    battery = dict(raw.get("battery", {}))
    for field_name in ("bat_temp", "bat_capacity", "bat_voltage", "bat_current"):
        if field_name in battery:
            battery[field_name] = venus_a_compatibility.scale_value(battery[field_name], field_name)

    return {
        "device": raw.get("device"),
        "wifi": raw.get("wifi"),
        "ble": raw.get("ble"),
        "battery": battery,
        "pv": raw.get("pv"),
        "mode": raw.get("mode"),
        "em": raw.get("em"),
        "_diagnostic": {"last_message_seconds": 5, "target_interval": 10, "actual_interval": 10},
        "_config": {"dod_percent": 88},
    }


@pytest.fixture
def sensor_map() -> dict[str, object]:
    """Dict of sensor key → description for fast lookup."""
    return {desc.key: desc for desc in SENSOR_TYPES}


@pytest.fixture
def pv_sensor_map() -> dict[str, object]:
    """Dict of PV sensor key → description."""
    return {desc.key: desc for desc in PV_SENSOR_TYPES}


@pytest.fixture
def binary_sensor_map() -> dict[str, object]:
    """Dict of binary sensor key → description."""
    return {desc.key: desc for desc in BINARY_SENSOR_TYPES}
