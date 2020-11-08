#pragma once

#include <string>
#include <condition_variable>

#include <bcm2835.h>

#include "device.h"
#include "constants.h"

class DeviceGpio : public Device {
    int gpio_addr;

 public:
    DeviceGpio(const std::string& name, DeviceType device_type, bool passive, int gpio_addr);
    ~DeviceGpio();

    void turn_on() const; 
    void turn_off() const;
    uint8_t read() const;
};
