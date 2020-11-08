#include <iostream>

#include "device_gpio.h"

DeviceGpio::DeviceGpio(const std::string& name, DeviceType device_type, bool passive, int gpio_addr)
    : Device(name, device_type, passive), gpio_addr(gpio_addr) {
}

void DeviceGpio::turn_on() const {
    std::cout << "Turned on " << name << " " << gpio_addr<< std::endl;
}

void DeviceGpio::turn_off() const {
    std::cout << "Turned off " << name << std::endl;
}

uint8_t DeviceGpio::read() const {
    std::cout << "Read from " << name << std::endl;

    return 1;
}
