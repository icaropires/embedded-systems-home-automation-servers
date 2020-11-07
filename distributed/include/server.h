#include <iostream>
#include <bitset>
#include <cassert>
#include <thread>
#include <atomic>
#include <csignal>
#include <stdexcept>
#include <vector>
#include <algorithm>

#include <stdio.h> 
#include <sys/socket.h> 
#include <arpa/inet.h> 
#include <unistd.h> 
#include <string.h> 
#include <sys/types.h>
#include <endian.h>

#include "device.h"
#include "device_gpio.h"
#include "constants.h"


class Server {
    typedef struct {
        uint8_t device_type;
        uint64_t states;
        float temperature;
        float umidity;
    } StatesMsg;

    float float_to_bigendian(float value){
        union convert {
            float f;
            unsigned int i;
        };

        union convert new_value;

        new_value.f = value;
        new_value.i = htonl(new_value.i);

        return new_value.f;
    }

    std::bitset<STATES_LEN> states;

    std::atomic<bool> continue_running, is_server_up;
    int server_socket = -1, client_socket = -1;

    // Index to make searches happen the same as in central server
    std::map<std::pair<DeviceType, int>, std::vector<Device>::const_iterator> idx_to_device;

 public:

    Server();

    ~Server();

    void start(const std::vector<Device>& devices);

    void stop();

 private:

    void serialize_states_msg(StatesMsg msg, uint8_t* buff);

    void client_loop();

    void apply_states(DeviceType device_type, const std::bitset<STATES_LEN>& new_states);

    void connection_handler(int socket);

    void server_loop();
};
