# hmc-clinic-msft-2020
Contains all work from the Harvey Mudd College 2020-2021 Microsoft Clinic team. 

This repository currently contains 
1. install scripts for installing a NGINX Server with a patch for Cloudflare's Quiche implementation of HTTP/3, a Caddy Server
2. scripts for testing HTTP/3 and HTTP/2 with simulated network conditions.
3. scripts for installing [Web Page Test!](https://github.com/WPO-Foundation/webpagetest).
4. scripts for seting up a client VM and a server VM on Azure.
3. dummy files as the payloads of the servers.
4. script for visualization the database.

This is designed to run on *Ubuntu 20.04*.

## Install
To set up a client VM, run the following in the desired directory:

    git clone https://github.com/JBoerma/hmc-clinic-msft-2020.git
    cd hmc-clinic-msft-2020/install/
    ./install-clients.sh
  
Similarly, to set up a server VM:

    git clone https://github.com/JBoerma/hmc-clinic-msft-2020.git
    cd hmc-clinic-msft-2020/install/
    ./install-servers.sh 
  
To install the servers and set up the environment, run the following on the server VM:
    ./install-all.sh
  
You can verify the install by visiting https://localhost

## Running the Script
This script will access a given URL using HTTP/2 and HTTP/3 under specified network conditions and with specific browsers, and return navigation timings using the PerformanceNavigationTiming interface, which implements the [Performance Timing Level 2](https://www.w3.org/TR/navigation-timing-2/) specification.
The script currently uses [tc-netem](https://www.man7.org/linux/man-pages/man8/tc-netem.8.html) to modify the network conditions, so root access is required.


### Dependencies
* Python 3.6+
* [playwright-python](https://github.com/microsoft/playwright-python)

#### Usage
    experiment.py [--device DEVICE] [--conditions CONDITIONS ...] [--browsers BROWSERS ...] [--url URL] [--runs RUNS] [--out OUT] [--throughput THROUGHPUT] [--payloads PAYLOADS] [--ports PORTS ...] [options]
    
#### Arguments
    --device DEVICE           Network device to modify [default: lo]
    --conditions CONDITIONS   List of network conditions [default: 4g-lte-good 3g-unts-good]
    --browsers BROWSERS       List of browsers to test [default: chromium edge]
    --throughput THROUGHPUT   Maximum number of request to send at a time [default: 1]
    --url URL                 URL to access [default: https://localhost]
    --runs RUNS               Number of runs in the experiment [default: 100]
    --out OUT                 File to output data to [default: results/results.db]
    --ports PORTS             List of ports to use (':443', ':444', ':445', ':446') [default: :443]
    --payloads PAYLOADS       List of sizes of the requsting payload [default: 100kb 1kb 10kb]

#### Options
    -h --help                 Show this screen 
    --disable_caching         Disables caching
    --warmup                  Warms up connection
    --async                   Run experiment asynchronously
    --qlog                    Turns on QLog logging

For example, to access a specific server 10 times through Firefox with a good 4g network, run:

    python3 experiment.py --browsers firefox --conditions 4g-lte-good --out results/data.db --url 10.0.0.0 --runs 10
    
The output of this script will be stored in two files:

In the client VM,
`results/data.db` contains the sqlite database, that stores the requests parameters, network condition, and navigation timings.

In the server VM
