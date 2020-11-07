#include "device.h"

// Must be outside main and in .cc
std::map<DeviceType, int> Device::id_counter;

Device::Device(const std::string& name, DeviceType device_type, bool passive)
    : name(name), type(device_type), passive(passive) {

    id = id_counter[device_type];
    id_counter[device_type] += 1;
}
