#include <iostream>
#include <bitset>
#include <cassert>
#include <thread>
#include <atomic>
#include <csignal>
#include <stdexcept>
#include <vector>
#include <algorithm>    // std::find

#include <stdio.h> 
#include <sys/socket.h> 
#include <arpa/inet.h> 
#include <unistd.h> 
#include <string.h> 
#include <sys/types.h>
#include <endian.h>

#include "constants.h"
#include "device.h"
#include "device_gpio.h"


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

    Server()
        : continue_running(true), is_server_up(false) {
    }

    ~Server() {
        stop();
    }

    void start(const std::vector<Device>& devices) {
        for(auto it = devices.begin(); it < devices.end(); ++it) {
            idx_to_device[{it->type, it->id}] = it;
        }

        std::thread t_server(&Server::server_loop, this);
        std::thread t_client(&Server::client_loop, this);

        t_server.join();
        t_client.join();
    }

    void stop() {
        continue_running = false;
        is_server_up = false;

        close(server_socket);
        close(client_socket);
    }

 private:

    void serialize_states_msg(StatesMsg msg, uint8_t* buff) {
        int pos = 0;

        memcpy(buff, (const void *) &msg.device_type, sizeof(msg.device_type));
        pos += sizeof(msg.device_type);

        uint64_t aux_llu = htobe64(msg.states);
        memcpy(buff+pos, (const void *) &aux_llu, sizeof(msg.states));
        pos += sizeof(msg.states);

        float aux_float = float_to_bigendian(msg.temperature);
        memcpy(buff+pos, (const void *) &aux_float, sizeof(msg.temperature));
        pos += sizeof(msg.temperature);

        aux_float = float_to_bigendian(msg.umidity);
        memcpy(buff+pos, (const void *) &aux_float, sizeof(msg.umidity));
        pos += sizeof(msg.umidity);

        assert(pos == STATES_MSG_LEN);
    }

    void client_loop() {
        if ((client_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0) { 
            perror("Unable to open client socket");
            exit(-1);
        } 

        struct timeval timeout;      
        timeout.tv_sec = 2;
        timeout.tv_usec = 0;

        if (setsockopt(client_socket, SOL_SOCKET, SO_SNDTIMEO, (char *)&timeout, sizeof(timeout)) < 0) {
            perror("Unable to set timeout");
        }

        struct sockaddr_in central_addr; 
        central_addr.sin_family = AF_INET; 
        central_addr.sin_addr.s_addr = inet_addr(HOST_CENTRAL);
        central_addr.sin_port = htons(PORT_CENTRAL); 

        if (connect(client_socket, (struct sockaddr *)&central_addr, sizeof(central_addr)) < 0) { 
            perror("Unable to connect to server");
            exit(-1);
        } 

        while(continue_running && is_server_up) {
            auto device_type = static_cast<uint8_t>(DeviceType::LAMP);
            StatesMsg msg{device_type, states.to_ullong(), 25.0, 50.0};

            uint8_t buff[STATES_MSG_LEN];
            serialize_states_msg(msg, buff);

            int sent = send(client_socket, buff, STATES_MSG_LEN, 0); 
            if(sent < 0) {
                perror("Failed to send states message"); }

            sleep(1);
        }
    }

    void apply_states(DeviceType device_type, const std::bitset<STATES_LEN>& new_states) {
        for(int i = 0; i <= STATES_LEN; i++) {
            bool is_on = (bool) new_states[i];  // Bitset iterates from left to right

            auto idx = std::make_pair(device_type, i);

            if(idx_to_device.count(idx)) {
                auto *p_device = (const Device *) &(*idx_to_device[idx]);

                if(p_device->passive) {
                    continue;
                }

                // Could add more types and checkings
                auto *gpio = (const DeviceGpio *) p_device;

                if (is_on) {
                    gpio->turn_on();
                } else {
                    gpio->turn_off();
                }
            } else {
                // Not registered device
            }
        }
    }

    void connection_handler(int socket) {
        while(continue_running) {
            uint8_t device_type_int = -1;

            if((recv(socket, (void *) &device_type_int, 1, 0)) < 0) {
                perror("Error receiving command");
                continue;
            }

            auto device_type = static_cast<DeviceType>(device_type_int);

            if(find(AUTO_TYPES.begin(), AUTO_TYPES.end(), device_type) == AUTO_TYPES.end()) {
                uint64_t states_int = -1;

                if((recv(socket, (void *) &states_int, 8, 0)) > 0) {
                    states_int = htobe64(states_int);
                    std::bitset<STATES_LEN> new_states(states_int);

                    std::cout << "Received states to " + DEVICE_TYPE_NAME.at(device_type) + ":" << std::endl;
                    std::cout << new_states.to_string() << std::endl << std::endl;

                    apply_states(device_type, new_states);
                } else {
                    perror("Error receiving states");
                    continue;
                }
            } else {
                std::cout << "Auto command received: " << std::endl;
            }
        }
    }

    void server_loop() {
        struct sockaddr_in distributed_addr; 
        distributed_addr.sin_family = AF_INET; 
        distributed_addr.sin_addr.s_addr = inet_addr("0.0.0.0");
        distributed_addr.sin_port = htons(PORT_DISTRIBUTED); 

        if((server_socket = socket(PF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0) {
            perror("Unable to open server socket");
            exit(1);
        }

        int enable = 1;
        if (setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(int)) < 0) {
            perror("Unable to config the socket");
            exit(1);
        }

        if(bind(server_socket, (struct sockaddr *) &distributed_addr, sizeof(distributed_addr)) < 0) {
            perror("Unable to bind server");
            exit(1);
        }

        if(listen(server_socket, 10) < 0) {
            perror("Failed to server start listening");
            exit(1);
        }

        is_server_up = true;
        while(continue_running) {
            struct sockaddr_in server_client_addr;
            socklen_t client_length = sizeof(server_client_addr);
            int socket_server_client = -1;

            if((socket_server_client = accept(server_socket, (struct sockaddr *) &server_client_addr, &client_length)) < 0) {
                perror("Unable to accept connection") ;
                continue;
            }

            std::string client_addr_str(inet_ntoa(server_client_addr.sin_addr));
            client_addr_str += ":" + std::to_string(ntohs(server_client_addr.sin_port));

            std::cout << "Connected to " << client_addr_str << std::endl;

            connection_handler(socket_server_client);

            close(socket_server_client);
            std::cout << "Closed connecttion to " << client_addr_str << std::endl;
        }
    }
};

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
    std::vector<Device> devices {
        DeviceGpio("Lâmpada 01 (Cozinha)", DeviceType::LAMP, false, 17),
        DeviceGpio("Lâmpada 02 (Sala)", DeviceType::LAMP, false, 18),
        DeviceGpio("Lâmpada 03 (Quarto 01)", DeviceType::LAMP, false, 27),
        DeviceGpio("Lâmpada 04 (Quarto 02)", DeviceType::LAMP, false, 22),
        DeviceGpio("Ar-Condicionado 01 (Quarto 01)", DeviceType::AIR_CONDITIONING, false, 23),
        DeviceGpio("Ar-Condicionado 02 (Quarto 02)", DeviceType::AIR_CONDITIONING, false, 24),
        // Device("Temperatura automática", DeviceType::AIR_CONDITIONING_AUTO),

        DeviceGpio("Sensor de Presença 01 (Sala)", DeviceType::SENSOR_PRESENCE, true, 25),
        DeviceGpio("Sensor de Presença 02 (Cozinha)", DeviceType::SENSOR_PRESENCE, true, 26),
        DeviceGpio("Sensor Abertura 01 (Porta Cozinha)", DeviceType::SENSOR_OPENNING, true, 5),
        DeviceGpio("Sensor Abertura 02 (Janela Cozinha)", DeviceType::SENSOR_OPENNING, true, 6),
        DeviceGpio("Sensor Abertura 03 (Porta Sala)", DeviceType::SENSOR_OPENNING, true, 12),
        DeviceGpio("Sensor Abertura 04 (Janela Sala)", DeviceType::SENSOR_OPENNING, true, 16),
        DeviceGpio("Sensor Abertura 05 (Janela Quarto 01)", DeviceType::SENSOR_OPENNING, true, 20),
        DeviceGpio("Sensor Abertura 06 (Janela Quarto 02)", DeviceType::SENSOR_OPENNING, true, 21),
    };

    server.start(devices);

    return 0; 
}
