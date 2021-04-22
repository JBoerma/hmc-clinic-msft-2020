## Set Up
Make sure that the client and the server VM is properly set up. Follow the [instruction](https://github.com/JBoerma/hmc-clinic-msft-2020#install) to finish seting up.
In the *Server VM*, run the following command to launch the servers (while inside the `install` directory)
```
./restart-all.sh
```
In the *Client VM*, run the following command to initialize network namespace for emulating conditions. This is to separate the SSH to the Azure from the SSH connection between Client and Server VM. 
```
./install/namespace.sh
```
Choose a network device when prompted. The newly created network namespace will be called *netns0*.

## Create Simulation
If we want to measure the timing of a connection over HTTP/3, we conduct an experiment using the *Client VM* and *Server VM*. 
The experiment.py script simulates an interaction between *Client VM* and *Server VM*, where the *Client VM* requests a file from *Server VM*.

```bash
experiment.py [--device DEVICE] [--conditions CONDITIONS ...] [--browsers BROWSERS ...] [--url URL] [--runs RUNS] [--out OUT] [--throughput THROUGHPUT] [--payloads PAYLOADS] [--ports PORTS ...] [options]
```

The users need to provide information to the fields below to properly simulate the connection:

```
--device                  What is the device to modify [e.g. veth-netns0]
--conditions              What is the network condition to simulate? [e.g. 4g-lte-good 3g-unts-good, a complete list of network condition]
--browsers                What is the browser that the Client uses? [e.g. edge, firefox, chromium]
--endpoints               What is the server? [e.g. 
                                              private: server-nginx, server-nginx-quiche, server-caddy, server-openlitespeed,
                                              public:  facebook, google, cloudflare]
--payloads PAYLOADS       What file does the client request? [e.g. 10kb.html, small, medium, large]
```

Optional fields to increase the accurazy 
#### Options
    -h --help                 Show this screen 
    --disable_caching         Disables caching
    --warmup                  Warms up connection
    --async                   Run experiment asynchronously
    --qlog                    Turns on QLog logging

For example, to access a specific server 10 times through Firefox with a good 4g network, run:

```bash
python3 experiment.py --browsers firefox --conditions 4g-lte-good --out results/data.db --url localhost --runs 10
```
## Collect Data

The output of this script will be stored in two files:

In the client VM,
`results/data.db` contains the sqlite database, that stores the requests parameters, network condition, and navigation timings.

In the server VM

## Using a Network Namespace

If starting tests through SSH on a VM, the experiments can throttle your connection if network conditions are simulated on the same device your SSH connection is going through. To prevent this, there is a script `install/namespace.sh` which initializes network namespace with a virtual ethernet device to simulate conditions on.

### Usage:

```
./install/namespace.sh
What network device do you want to use?
 lo:
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:
 wlo1:
    link/ether b4:69:21:e8:1e:fd brd ff:ff:ff:ff:ff:
 enx000ec6aeac34:
    link/ether 00:0e:c6:ae:ac:34 brd ff:ff:ff:ff:ff:
 docker0:
    link/ether 02:42:20:76:74:0e brd ff:ff:ff:ff:ff:

lo
lo
```

Running the script will initially print out all currently connected devices. Type the name of the desired device to run experiments on, and the script will create a new network namespace that can connect to other networks through that device. 

In order to run experiments inside the namespace, run:

```bash
sudo ip netns exec netns0 sudo -u $USER python3 experiment.py --device veth-netns0
```

Followed by any desired experiment parameters.
