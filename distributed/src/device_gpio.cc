#include <iostream>
#include <mutex>

#include "device_gpio.h"

std::mutex mutex_pin;

DeviceGpio::DeviceGpio(const std::string& name, DeviceType device_type, bool passive, int gpio_addr)
        : Device(name, device_type, passive), gpio_addr(gpio_addr) {

    // Setup just once was getting segmentation fault 

    if (!bcm2835_init()) {
        throw std::runtime_error("Unable to start bcm2835 GPIO write");    
    }

    // Switch order will break writing
    bcm2835_gpio_fsel(gpio_addr, BCM2835_GPIO_FSEL_INPT);
    bcm2835_gpio_fsel(gpio_addr, BCM2835_GPIO_FSEL_OUTP);
}

DeviceGpio::~DeviceGpio() {
    // bcm2835_close();  // Segmentation fault if enabled
}

void DeviceGpio::turn_on() const {
    std::lock_guard<std::mutex> lock(mutex_pin);

    bcm2835_gpio_write(gpio_addr, HIGH);
}

void DeviceGpio::turn_off() const {
    std::lock_guard<std::mutex> lock(mutex_pin);

    bcm2835_gpio_write(gpio_addr, LOW);
}

uint8_t DeviceGpio::read() const {
    std::lock_guard<std::mutex> lock(mutex_pin);

    return bcm2835_gpio_lev(gpio_addr);;
}
