#include <unistd.h> 
#include <iostream>

#include "server.h"
#include "constants.h"
#include "device.h"
#include "device_gpio.h"
#include "environment_sensor.h"

Server server;

void exit_handler(int) {
    server.stop();
    std::cout << "Exitting..." << std::endl;

    sleep(1);  // Let stuff finish
    kill(getpid(), SIGUSR1);  // Not ideal, but interrupt accept
}

int main() { 
    signal(SIGINT, exit_handler);
    signal(SIGTERM, exit_handler);

    // MUST be same order registered in central server!
    std::vector<DeviceGpio> devices {
        DeviceGpio("Lâmpada 01 (Cozinha)", DeviceType::LAMP, false, 17),
        DeviceGpio("Lâmpada 02 (Sala)", DeviceType::LAMP, false, 18),
        DeviceGpio("Lâmpada 03 (Quarto 01)", DeviceType::LAMP, false, 27),
        DeviceGpio("Lâmpada 04 (Quarto 02)", DeviceType::LAMP, false, 22),
        DeviceGpio("Ar-Condicionado 01 (Quarto 01)", DeviceType::AIR_CONDITIONING, false, 23),
        DeviceGpio("Ar-Condicionado 02 (Quarto 02)", DeviceType::AIR_CONDITIONING, false, 24),

        DeviceGpio("Sensor de Presença 01 (Sala)", DeviceType::SENSOR_PRESENCE, true, 25),
        DeviceGpio("Sensor de Presença 02 (Cozinha)", DeviceType::SENSOR_PRESENCE, true, 26),
        DeviceGpio("Sensor Abertura 01 (Porta Cozinha)", DeviceType::SENSOR_OPENNING, true, 5),
        DeviceGpio("Sensor Abertura 02 (Janela Cozinha)", DeviceType::SENSOR_OPENNING, true, 6),
        DeviceGpio("Sensor Abertura 03 (Porta Sala)", DeviceType::SENSOR_OPENNING, true, 12),
        DeviceGpio("Sensor Abertura 04 (Janela Sala)", DeviceType::SENSOR_OPENNING, true, 16),
        DeviceGpio("Sensor Abertura 05 (Janela Quarto 01)", DeviceType::SENSOR_OPENNING, true, 20),
        DeviceGpio("Sensor Abertura 06 (Janela Quarto 02)", DeviceType::SENSOR_OPENNING, true, 21),

        // // DeviceGpio("Temperatura automática", DeviceType::AIR_CONDITIONING_AUTO, false, -1),  // TODO: this is not Gpio
    };

    EnvironmentSensor env_sensor("/dev/i2c-1");
    server.start(devices, env_sensor);

    server.stop();
    return 0; 
}
