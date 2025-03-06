"""Sensor platform for Northern Powergrid Power Cuts integration."""
import logging
import asyncio
import aiohttp
import async_timeout
import json
from datetime import datetime, timezone

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.entity import Entity, EntityCategory
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    ATTRIBUTION,
    SCAN_INTERVAL,
    API_ENDPOINT,
    CONF_POSTCODE,
    CONF_NAME,
    DEFAULT_NAME,
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Required(CONF_POSTCODE): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Northern Powergrid Power Cuts sensor from a config entry."""
    name = config_entry.data.get(CONF_NAME, DEFAULT_NAME)
    postcode = config_entry.data.get(CONF_POSTCODE)

    session = async_get_clientsession(hass)
    coordinator = PowerCutDataUpdateCoordinator(hass, session, postcode)

    await coordinator.async_refresh()

    # IMPORTANT: First create and add the main device
    main_entity = PowerCutCountSensor(coordinator, name, postcode, config_entry.entry_id)
    async_add_entities([main_entity], True)
    
    # Wait for the first entity to be fully set up
    await asyncio.sleep(1)
    
    # Now add the child entities that reference the main device
    if coordinator.data:
        child_entities = []
        for i, power_cut in enumerate(coordinator.data):
            prefix = f"power_cut_{i+1}"
            
            # Create entities for this power cut
            child_entities.append(
                PowerCutReferenceSensor(
                    coordinator, f"{name} {prefix} Reference", 
                    postcode, config_entry.entry_id, i
                )
            )
            child_entities.append(
                PowerCutAffectedCustomersSensor(
                    coordinator, f"{name} {prefix} Affected Customers", 
                    postcode, config_entry.entry_id, i
                )
            )
            child_entities.append(
                PowerCutStatusSensor(
                    coordinator, f"{name} {prefix} Status", 
                    postcode, config_entry.entry_id, i
                )
            )
            child_entities.append(
                PowerCutReasonSensor(
                    coordinator, f"{name} {prefix} Reason", 
                    postcode, config_entry.entry_id, i
                )
            )
            child_entities.append(
                PowerCutStartTimeSensor(
                    coordinator, f"{name} {prefix} Start Time", 
                    postcode, config_entry.entry_id, i
                )
            )
            child_entities.append(
                PowerCutEstimatedRestorationSensor(
                    coordinator, f"{name} {prefix} Estimated Restoration", 
                    postcode, config_entry.entry_id, i
                )
            )
            child_entities.append(
                PowerCutNatureSensor(
                    coordinator, f"{name} {prefix} Nature", 
                    postcode, config_entry.entry_id, i
                )
            )
        
        if child_entities:
            async_add_entities(child_entities, True)


class PowerCutDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching power cut data."""

    def __init__(self, hass, session, postcode):
        """Initialize."""
        self.session = session
        self.postcode = postcode.upper().replace(" ", "")

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch data from Northern Powergrid API."""
        try:
            with async_timeout.timeout(10):
                response = await self.session.get(API_ENDPOINT)
                # The API returns text/plain but contains JSON data
                text_data = await response.text()
                data = json.loads(text_data)

                # Filter by postcode
                filtered_data = []
                for power_cut in data:
                    if power_cut.get("Postcode"):
                        api_postcode = power_cut["Postcode"].upper().replace(" ", "")
                        if self.postcode in api_postcode:
                            filtered_data.append(power_cut)

                return filtered_data
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}")


class PowerCutBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Northern Powergrid Power Cut sensors."""

    def __init__(self, coordinator, name, postcode, entry_id, power_cut_index=None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._postcode = postcode
        self._entry_id = entry_id
        self._power_cut_index = power_cut_index
        self._attr_attribution = ATTRIBUTION

    @property
    def available(self):
        """Return if entity is available."""
        if self._power_cut_index is not None and self.coordinator.data:
            # Only available if the specific power cut still exists
            return (len(self.coordinator.data) > self._power_cut_index and 
                    self.coordinator.last_update_success)
        return self.coordinator.last_update_success

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_info(self):
        """Return device info."""
        if self._power_cut_index is not None:
            # Get reference for device name if available
            reference = ""
            if (self.coordinator.data and 
                len(self.coordinator.data) > self._power_cut_index):
                reference = self.coordinator.data[self._power_cut_index].get("Reference", "")
            
            return {
                "identifiers": {
                    (DOMAIN, f"{self._entry_id}_power_cut_{self._power_cut_index}")
                },
                "name": f"Power Cut {reference}",
                "manufacturer": "Northern Powergrid",
                "model": "Power Cut",
                "via_device": (DOMAIN, self._entry_id),
            }
        else:
            return {
                "identifiers": {
                    (DOMAIN, self._entry_id)
                },
                "name": f"Northern Powergrid {self._postcode}",
                "manufacturer": "Northern Powergrid",
                "model": "Power Cuts API",
            }


class PowerCutCountSensor(PowerCutBaseSensor):
    """Sensor showing number of active power cuts."""

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._entry_id}_count"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return "0"
        return str(len(self.coordinator.data))

    @property
    def icon(self):
        """Return the icon of the sensor."""
        if self.coordinator.data and len(self.coordinator.data) > 0:
            return "mdi:flash-off"
        return "mdi:flash"
        
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "postcode": self._postcode,
        }


class PowerCutReferenceSensor(PowerCutBaseSensor):
    """Sensor for power cut reference."""

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._entry_id}_power_cut_{self._power_cut_index}_reference"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data or len(self.coordinator.data) <= self._power_cut_index:
            return None
        return self.coordinator.data[self._power_cut_index].get("Reference")
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:pound"


class PowerCutAffectedCustomersSensor(PowerCutBaseSensor):
    """Sensor for affected customers."""

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._entry_id}_power_cut_{self._power_cut_index}_affected_customers"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data or len(self.coordinator.data) <= self._power_cut_index:
            return None
        return self.coordinator.data[self._power_cut_index].get("TotalConfirmedPowerCut")
    
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:account-group"


class PowerCutStatusSensor(PowerCutBaseSensor):
    """Sensor for power cut status."""

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._entry_id}_power_cut_{self._power_cut_index}_status"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data or len(self.coordinator.data) <= self._power_cut_index:
            return None
        return self.coordinator.data[self._power_cut_index].get("CustomerStageSequenceMessage")
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:information-outline"


class PowerCutReasonSensor(PowerCutBaseSensor):
    """Sensor for power cut reason."""

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._entry_id}_power_cut_{self._power_cut_index}_reason"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data or len(self.coordinator.data) <= self._power_cut_index:
            return None
        return self.coordinator.data[self._power_cut_index].get("Reason")
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:help-circle-outline"


class PowerCutStartTimeSensor(PowerCutBaseSensor):
    """Sensor for power cut start time."""
    
    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.TIMESTAMP

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._entry_id}_power_cut_{self._power_cut_index}_start_time"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data or len(self.coordinator.data) <= self._power_cut_index:
            return None
        
        time_str = self.coordinator.data[self._power_cut_index].get("LoggedTime")
        if not time_str:
            return None
            
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.isoformat()
        except (ValueError, TypeError):
            return None
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:clock-start"


class PowerCutEstimatedRestorationSensor(PowerCutBaseSensor):
    """Sensor for estimated restoration time."""
    
    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.TIMESTAMP

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._entry_id}_power_cut_{self._power_cut_index}_estimated_restoration"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data or len(self.coordinator.data) <= self._power_cut_index:
            return None
        
        time_str = self.coordinator.data[self._power_cut_index].get("EstimatedTimeTillResolution")
        if not time_str:
            return None
            
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.isoformat()
        except (ValueError, TypeError):
            return None
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:clock-end"


class PowerCutNatureSensor(PowerCutBaseSensor):
    """Sensor for nature of outage."""

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._entry_id}_power_cut_{self._power_cut_index}_nature"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data or len(self.coordinator.data) <= self._power_cut_index:
            return None
        return self.coordinator.data[self._power_cut_index].get("NatureOfOutage")
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:flash-alert"