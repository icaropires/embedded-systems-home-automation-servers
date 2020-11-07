#include <iostream>
#include <bitset>
#include <cassert>

#include <stdio.h> 
#include <sys/socket.h> 
#include <arpa/inet.h> 
#include <unistd.h> 
#include <string.h> 
#include <sys/types.h>
#include <endian.h>


#define HOST_CENTRAL "127.0.0.1"
#define PORT_CENTRAL 10008

#define STATES_MSG_LEN 17  // bytes
#define STATES_LEN 64  // bits

typedef struct {
    uint8_t device_type;
    unsigned long long states;
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

int main() { 
    std::bitset<STATES_LEN> states;

    int client_socket = 0; 

    if ((client_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0) { 
        perror("Unable to create the socket");
        return -1; 
    } 

    struct sockaddr_in server_addr; 
    server_addr.sin_family = AF_INET; 
    server_addr.sin_addr.s_addr = inet_addr(HOST_CENTRAL);
    server_addr.sin_port = htons(PORT_CENTRAL); 

    if (connect(client_socket, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) { 
        perror("Unable to connect to server");
        return -1; 
    } 

    // uint8_t buff[STATES_MSG_LEN];
    StatesMsg msg{1, states.to_ullong(), 25.0, 50.0};

    uint8_t buff[STATES_MSG_LEN];
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

    int sent = send(client_socket, buff, STATES_MSG_LEN, 0); 
    if(sent < 0) {
        perror("Failed to sent states message");
    }

    // char buffer[1024]; 
    // int result = read(client_socket, buffer, 1024); 
    // printf("%s\n", buffer); 

    return 0; 
}
