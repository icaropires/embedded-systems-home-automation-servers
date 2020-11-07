#pragma once

#include <string>

#include "constants.h"

class Device {

 private:
    static std::map<DeviceType, int> id_counter;

 public:
    std::string name;
    DeviceType type;
    unsigned int id;
    bool passive;

    Device(const std::string& name, DeviceType device_type, bool passive);
    // virtual ~Device() = default;
};
