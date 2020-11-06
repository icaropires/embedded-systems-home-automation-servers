from enum import Enum


HOST_CENTRAL = ''
PORT_CENTRAL = 10008

PORT_DISTRIBUTED = 10108

CommandType = Enum('CommandType', 'ON_OR_OFF AUTO')
DeviceType = Enum('DeviceType', 'SENSOR_OPENNING SENSOR_PRESENCE LAMP AIR_CONDITIONING')

# Device types that will trigger alarm if activated
ALARM_TYPES = (DeviceType.SENSOR_OPENNING, DeviceType.SENSOR_PRESENCE)

# Passive device types can't manually turned on or off
PASSIVE_TYPES = (DeviceType.SENSOR_OPENNING, DeviceType.SENSOR_PRESENCE)

# Name for device which represents automatic control of air conditionings
AUTO_DEVICE_NAME = 'Temperatura Automática'
