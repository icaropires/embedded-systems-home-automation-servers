from enum import Enum


HOST_CENTRAL = ''
PORT_CENTRAL = 10008

PORT_DISTRIBUTED = 10108

DeviceType = Enum(
    'DeviceType',
    'SENSOR_OPENNING SENSOR_PRESENCE LAMP AIR_CONDITIONING AIR_CONDITIONING_AUTO'
)

# Device types that will trigger alarm if activated
ALARM_TYPES = (DeviceType.SENSOR_OPENNING, DeviceType.SENSOR_PRESENCE)

# Types which have automatic control
AUTO_TYPES = (DeviceType.AIR_CONDITIONING_AUTO,)
