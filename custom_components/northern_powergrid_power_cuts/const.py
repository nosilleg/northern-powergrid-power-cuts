"""Constants for the Northern Powergrid Power Cuts integration."""
from datetime import timedelta

DOMAIN = "northern_powergrid_power_cuts"
ATTRIBUTION = "Data provided by Northern Powergrid"

CONF_POSTCODE = "postcode"
CONF_NAME = "name"
DEFAULT_NAME = "Northern Powergrid Power Cut"
SCAN_INTERVAL = timedelta(minutes=15)
API_ENDPOINT = "https://power.northernpowergrid.com/Powercut_API/rest/powercuts/getall"