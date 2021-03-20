# hmc-clinic-msft-2020
Contains all work from the Harvey Mudd College 2020-2021 Microsoft Clinic team. 

# Collect System Utility

System utility does two things:

(1) logs the cpu time of the processs: scans through all the running process every second, to find the process that runs the browser, and get the cpu time. 

(2) logs the iowait of the system: every second, get the iowait measurement

## Usage

```python
# start logging the measurements
python3 systemUtil.py 

# interupt the program to write the measurements to a file
press control + c
```

# Visualize Data

Generates CDF plots for navigation timing events, using pandas´s DataFrame, numpy, and matplotlid

## Usage

```python
python3 visualization.py --dir results/firefoxdelay15ms16/11/2020\ 09\:14\:16.csv --output graph/firefoxdelay15ms16
```

command line arguments:

```bash
usage: visualization.py [-h] --dir FILE --output FILE

basic vitualization for data specified

optional arguments:
  -h, --help            show this help message and exit
  --dir FILE, -d FILE   read data from FILE
  --output FILE, -o FILE
                        save output to FILE
```

## Using Network Namespace

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

Running the script will initially print out all currently connected devices. Type the name of the desired device to run experiments on, and the script will create a new network namespace that can connect to other networks through that device. In order to run experiments inside the namespace, run:

```bash
sudo ip netns exec netns0 sudo -u $USER python3 experiment.py --device veth-netns0
```

Followed by any desired experiment parameters.