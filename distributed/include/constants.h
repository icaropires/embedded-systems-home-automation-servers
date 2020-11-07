#pragma once

#include <map>
#include <vector>

#define HOST_CENTRAL "127.0.0.1"
#define PORT_CENTRAL 10008

#define PORT_DISTRIBUTED 10108

#define STATES_MSG_LEN 17  // bytes
#define STATES_LEN 64  // bits

enum class DeviceType {SENSOR_OPENNING = 1, SENSOR_PRESENCE, LAMP, AIR_CONDITIONING, AIR_CONDITIONING_AUTO};

const std::map<DeviceType, std::string> DEVICE_TYPE_NAME {
    {DeviceType::SENSOR_OPENNING, "SENSOR_OPENNING"},
    {DeviceType::SENSOR_PRESENCE, "SENSOR_PRESENCE"},
    {DeviceType::LAMP, "LAMP"},
    {DeviceType::AIR_CONDITIONING, "AIR_CONDITIONING"},
    {DeviceType::AIR_CONDITIONING_AUTO, "AIR_CONDITIONING_AUTO"},
};

const std::vector<DeviceType> AUTO_TYPES{DeviceType::AIR_CONDITIONING_AUTO,};
