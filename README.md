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

```
usage: visualization.py [-h] --dir FILE --output FILE

basic vitualization for data specified

optional arguments:
  -h, --help            show this help message and exit
  --dir FILE, -d FILE   read data from FILE
  --output FILE, -o FILE
                        save output to FILE
```