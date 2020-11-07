#include <iostream>
#include <bitset>
#include <cassert>
#include <thread>
#include <atomic>
#include <csignal>
#include <stdexcept>
#include <vector>
#include <map>
#include <algorithm>    // std::find

#include <stdio.h> 
#include <sys/socket.h> 
#include <arpa/inet.h> 
#include <unistd.h> 
#include <string.h> 
#include <sys/types.h>
#include <endian.h>


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

 public:

    Server()
        : continue_running(true), is_server_up(false) {

    }

    ~Server() {
        stop();
    }

    void start() {
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
    std::cout << "Exitting.." << std::endl;

    sleep(1);  // Let stuff finish
    kill(getpid(), SIGUSR1);  // Not ideal, but interrupt accept
}

int main() { 
    signal(SIGINT, exit_handler);
    signal(SIGTERM, exit_handler);

    server.start();

    return 0; 
}
