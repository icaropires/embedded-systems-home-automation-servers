# Embedded Systems - Home Automation Servers

The objective of this application is to control an simulated environment for home automation. It is a college project from the discipline of Fundamentals of Embedded Systems. The complete description is here [project description](https://gitlab.com/fse_fga/projetos/projeto-2).

## Demonstration

![demonstration](doc/demonstration.png)


## Building

The code was developed and tested in two Raspberries Pi.

### External dependencies

These are dependencies which are not cloned with this repository:

* [OMX Player](https://www.raspberrypi.org/documentation/usage/audio/) (For sounding the alarm)

1. Clone the repository:

``` bash
git clone --recursive https://github.com/icaropires/embedded-temperature-on-off
```

2. `cd` into project's dir and build it:

``` bash
cd embedded-systems-home-automation-servers/distributed
make
```

Install Python dependencies from root project:

``` bash
pip3 install -r central/requirements.txt --user  # better inside a virtual environment than --user
```

## Running

With the dependencies installed and code built run the central server:

```bash
python3 central/central.py
```

And the distributed server:

``` bash
distributed/bin/bin
```

Without the needed hardware for the distributed, you can also run [mock.py](scripts/mock.py).

## Some more details

* There are two servers, a distributed one and a central one (could be expanded to more distributed servers)
* Servers communicate to each other through TCP protocol
* Central server communicates with the sensors and actuators
* Central server runs a terminal based UI, which controls the distributed server
* The application is heavily based in devices being identified by a type and an id
* Types are represented by 8 bits in payloads and enums in code
* State from a specific type is represented by 64 bits
* Each bit from state represents a device, so there is a limitation of 64 devices for each type
* Device with `id = 0` is represented by the least significant bit from state, the one with id 1 the second bit from right to left and so on
* Big endian is used for network communication

## TODO

* Control Temperature with on/off [#1](https://github.com/icaropires/embedded-systems-home-automation-servers/issues/1)
* Devices are turned off on disconect only if the distributed server disconnect but not if the central
* Exitting the UI don't close the connection, only when stops the distributed server
