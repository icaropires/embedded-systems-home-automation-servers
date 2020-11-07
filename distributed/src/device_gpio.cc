#include <iostream>

#include "device_gpio.h"

DeviceGpio::DeviceGpio(const std::string& name, DeviceType device_type, bool passive, int gpio_addr)
    : Device(name, device_type, passive), gpio_addr(gpio_addr) {
}

void DeviceGpio::turn_on() const {
    std::cout << "Turned on " << name << ' ' << std::endl;
}

void DeviceGpio::turn_off() const {
    std::cout << "Turned off " << name << ' ' << id << std::endl;
}
