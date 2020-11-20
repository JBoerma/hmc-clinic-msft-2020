# hmc-clinic-msft-2020
Contains all work from the Harvey Mudd College 2020-2021 Microsoft Clinic team. 

This repository currently contains an install script for the NGINX Server with a patch for Cloudflare's Quiche implementation of HTTP/3, and a script for testing HTTP/3 and HTTP/2 with simulated network conditions. This is designed to run on Ubuntu 20.04.

## Server Install
To install the NGINX server, run the following in the desired directory:

    git clone https://github.com/JBoerma/hmc-clinic-msft-2020.git
    cd hmc-clinic-msft-2020/install/
    ./nginx-quiche.sh
  
You can verify the install by visiting https://localhost

## Running the Script
This script will access a given URL using HTTP/2 and HTTP/3 under specified network conditions and with specific browsers, and return navigation timings using the PerformanceNavigationTiming interface, which implements the [Performance Timing Level 2](https://www.w3.org/TR/navigation-timing-2/) specification.
The script currently uses [tc-netem](https://www.man7.org/linux/man-pages/man8/tc-netem.8.html) to modify the network conditions, so root access is required.

### Dependencies
* Python 3.6+
* [playwright-python](https://github.com/microsoft/playwright-python)

#### Usage:

    python3 experiment.py experiment.py [--device DEVICE] [--options OPTIONS] [--browsers BROWSERS] 
                                          [--url URL] [--runs RUNS] [options]
    
#### Arguments:

    --device DEVICE           Network device to modify [default: lo root]
    --options OPTIONS         tc-netem conditions to apply [default: delay 0ms]
    --browsers BROWSERS       List of browsers to test [default: firefox,chromium,edge]
    --url URL                 URL to access [default: https://localhost]
    --runs RUNS               Number of runs in the experiment [default: 1]

#### Options:

    -h --help                 Display usage
    --disable_caching         Disables caching

For example, to access the localhost server 10 times through Firefox, Chromium, and Edge with a latency of 100ms and packet loss of 25%, run:

    python3 experiment.py --options "delay 100ms loss 25%"
    
The output of this script will be stored in two files:

`main.csv` contains the unique ID for the experiment, the git hash, the webpage accessed, and the tc-netem options entered.

`<experimentID>csv`, which is named for the experiment ID, contains rows of individual runs, which each have the navigation timings, browser, and HTTP version.
