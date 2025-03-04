# Northern Powergrid Power Cuts for Home Assistant

This integration provides information about power cuts in the Northern Powergrid areas of Northeast England, Yorkshire and northern Lincolnshire.

## Features

- Shows current power cuts affecting your postcode
- Displays details about each power cut including:
  - Reference number
  - Number of affected customers
  - Current status
  - Reason for the power cut
  - Start time
  - Estimated restoration time
  - Nature of the outage

## Installation

### HACS Installation

1. Ensure [HACS](https://hacs.xyz/) is installed
2. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ (top right) → Custom repositories
   - URL: `https://github.com/nosilleg/ha-northern-powergrid-power-cuts`
   - Category: Integration
3. Click "Add"
4. Search for "Northern Powergrid Power Cuts" in the Integrations tab
5. Click Install

### Manual Installation

1. Download the latest release
2. Copy the `northern_powergrid_power_cuts` folder to your `custom_components` folder
3. Restart Home Assistant

## Configuration

This integration can be configured via the Home Assistant UI. No YAML configuration is required. Simply go to Integrations and add "Northern Powergrid Power Cuts". You will be prompted for your postcode.

## Lovelace UI Examples

Here are some examples of how to use the Northern Powergrid Power Cuts integration in your Lovelace UI.

### Basic Card

This card shows the number of power cuts currently affecting your area.

```yaml
type: entities
entities:
  - entity: sensor.northern_powergrid_power_cut_count
```

### Conditional Card

This card shows a warning if there are any power cuts affecting your area. It also displays the reason and estimated restoration time for the first power cut.

```yaml
type: conditional
conditions:
  - entity: sensor.northern_powergrid_power_cut_count
    state_not: "0"
card:
  type: markdown
  content: >
    ## ⚡ Power Cut Detected ⚡

    There are currently {{states('sensor.northern_powergrid_power_cut_count')}} power cuts affecting
    your area.

    **Reason:** {{states('sensor.northern_powergrid_power_cut_reason')}}

    **Estimated Restoration:** 
    {{states('sensor.northern_powergrid_power_cut_estimated_restoration')}}
```

### Detailed Card

This card shows all the details for each power cut.

```yaml
type: entities
entities:
  - entity: sensor.northern_powergrid_power_cut_reference
  - entity: sensor.northern_powergrid_power_cut_affected_customers
  - entity: sensor.northern_powergrid_power_cut_status
  - entity: sensor.northern_powergrid_power_cut_reason
  - entity: sensor.northern_powergrid_power_cut_start_time
  - entity: sensor.northern_powergrid_power_cut_estimated_restoration
  - entity: sensor.northern_powergrid_power_cut_nature
```

## Data Attribution

All data is provided by [Northern Powergrid](https://www.northernpowergrid.com/power-cuts-map) and is updated every 15 minutes.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
