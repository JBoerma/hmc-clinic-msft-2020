import subprocess, json, csv, os
from sqlite3 import Connection, connect
from datetime import datetime
from tqdm import tqdm

import logging
logger = logging.getLogger()

"""
A dictionary that maps network condition in string to a tuple of tc parameters
realistic parameters are obtained here:
https://www.browserstack.com/docs/automate/selenium/simulate-network-conditions
"""
condition_to_params = {
    # network condition   (latency, packetloss, bandwidth(download speed))
    "2g-gprs-good":         (500, 1, 50),
    "2g-gprs-lossy":        (650, 2, 30),
    "edge-good":            (300, 0, 250),
    "edge-lossy":           (500, 1, 150),
    "3g-unts-good":         (100, 0, 400),
    "3g-umts-lossy":        (200, 1, 200),
    "3.5g-hspa-good":       (100, 0, 1800),
    "3.5g-hspa-lossy":      (190, 1, 900),
    "3.5g-hspa-plus-good":  (100, 0, 7000),
    "3.5g-hspa-plus-lossy": (130, 1, 2000),
    "4g-lte-good":          (100, 0, 18000),
    "4g-lte-high-latency":  (3000, 0, 18000),
    "4g-lte-lossy":         (120, 1, 7000),
    "4g-lte-advanced-good": (80, 0, 25000),
    "4g-lte-advanced-lossy":(70, 1, 15000),
}

"""
TC command templetes for emulating
latency/loss (https://man7.org/linux/man-pages/man8/tc-netem.8.html) 
and bandwidth using TBF (https://man7.org/linux/man-pages/man8/tc-tbf.8.html)
Applying both latency/loss and bandwidth, according to
https://lists.linuxfoundation.org/pipermail/netem/2007-April/001101.html

"""
APPLY_LATENCY_LOSS  = "sudo tc qdisc add dev {DEVICE} root handle 1:0 netem delay {LATENCY}ms loss {LOSS}%"
APPLY_LATENCY  = "sudo tc qdisc add dev {DEVICE} root handle 1:0 netem delay {LATENCY}ms"
# TODO: we are still not sure whether this emulates the desired network conditions, specifically we are not sure how to 
# set the value of `burst` or `limit`, will need to further investigate into this
APPLY_BANDWIDTH  = "sudo tc qdisc add dev {DEVICE} parent 1:1 handle 10: tbf rate {BANDWIDTH}kbps burst {BURST} limit {LIMIT}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE} root"

"""
Emulate the network condition using TC netem and TBF
"""
def apply_condition(
    device: str, 
    condition: str,
    ):
    try:
        latency, loss, bandwidth = condition_to_params[condition]
    except KeyError:
        # Basic attempt to add in custom tc condition
        latency, loss, bandwidth = map(int,condition.split(' '))
    print(latency, loss, bandwidth)

    # handeling tc errors
    command_status = 0
    command = ""
    if loss == 0:
        command = APPLY_LATENCY.format(DEVICE = device, LATENCY = latency)
    else:
        command = APPLY_LATENCY_LOSS.format(DEVICE = device, LATENCY = latency, LOSS = loss)

    command_status = run_tc_command(command)
    # if we have had some trouble setting tc, remove all the previous TC settings, and try setting tc again
    if command_status == 1: # this means that we had some trouble running tc!
        reset_condition(device) # the trouble should be able to be fixed with removing all the previous setting
        logger.debug("reseting condition")
        retry_command_status = run_tc_command(command)
        if retry_command_status == 0:
            logger.debug("reset tc command!")
        else:

            logger.error("RESET TC COMMAND FAILED") # if resetting tc does not work, we will keep track of the error
    # applying the second tc command
    run_tc_command(APPLY_BANDWIDTH.format(DEVICE = device, BANDWIDTH = bandwidth, BURST = bandwidth, LIMIT = 2*bandwidth))

"""
Removing the previous TC settings
"""
def reset_condition(
    device: str, 
    ):
    run_tc_command(RESET_FORMAT.format(DEVICE = device))

"""
Apply the given TC command using subprocess
Return 1 if there is some issue running TC
Return 0 if TC runs successfully
"""
def run_tc_command(
    command: str,
):
    if command:
        logger.info(f"commands are {command}")
        result = subprocess.run(command.split())
        if result.returncode > 0:
            # Info because this error is logged higher up in the execution tree
            logger.info("Issue running TC!")
            logger.info(str(result.args))
            logger.info(str(result.stderr))
            logger.info("--------------------------")
            return 1 # failed
        return 0 #success

"""
Headers/columns of different tables in the sqlite database
for details, please refer to the documentation of Schema
https://docs.google.com/spreadsheets/d/13Ao_zlXyoTtynbOXBAuh_GHTQAvVtB0YMq-Z6y5Szjs/edit#gid=0
"""
big_table_fmt = {
    "schemaVer" : "TEXT",
    "experimentID" : "TEXT",
    "webPage" : "TEXT",
    "serverVersion" : "TEXT",
    "gitHash" : "TEXT",
    "condition" : "TEXT",
    }

monitoring_fmt = {
    "experimentID" : "TEXT",
    "currentTime" : "TEXT",
    "unixTime" : "INT",
    "currentProcNames" : "TEXT",
    "cpuTime" : "TEXT",
    "ioWait" : "INT",
    "load_1": "Float",
    "load_5": "Float",
    "load_15": "Float",
    }

timings_fmt = {
    "experimentID" : "TEXT",
    "browser" : "TEXT",
    "server" : "TEXT",
    "httpVersion" : "TEXT",
    "payloadSize" : "TEXT",
    "warmup" : "BOOL",
    "netemParams" : "TEXT",
    "startTime" : "Float",
    "fetchStart" : "Float",
    "domainLookupStart" : "Float",
    "domainLookupEnd" : "Float",
    "connectStart" : "Float", 
    "secureConnectionStart" : "Float",
    "connectEnd" : "Float", 
    "requestStart" : "Float", 
    "responseStart" : "Float", 
    "responseEnd" : "Float",
    "domInteractive" : "Float",
    "domContentLoadedEventStart" : "Float", 
    "domContentLoadedEventEnd" : "Float", 
    "domComplete" : "Float", 
    "loadEventStart" : "Float",
    "loadEventEnd" : "Float",
    "error" : "TEXT",
}

processes_fmt = {
    "unixTime" : "INT",
    "user" : "TEXT",
    "pid" : "INT",
    "CPUPercent" : "Float",
    "MemoryPercent" : "Float",
    "VSZ" : "INT",
    "RSS" : "INT",
    "TTY" : "TEXT",
    "stat": "TEXT",
    "start": "TEXT",
    "Time": "TEXT",
    "commmand": "TEXT"
    }

# the default output database
out = "results/results.db"

"""
Set up the database in the output directory
return the handle/reference of the database
"""
def setup_data_file_headers(
    out: str
):
    # If this database is an previous database, directly return the reference.
    # However, if the existing database is set up with different headers,
    # we will run into error when try to write to the database
    if os.path.exists(out):
        return connect(out)
    
    # If directory doesn't exist, can't connect
    # Create a new database
    if out != ":memory:":
        os.makedirs(os.path.dirname(out), exist_ok = True)

    # Create headers for new database
    # Generate statements that creates and populates database tables
    big_table = ""
    for key in big_table_fmt.keys():
        big_table += f"{key} {big_table_fmt[key]}, "
    monitoring = ""
    for key in monitoring_fmt.keys():
        monitoring += f"{key} {monitoring_fmt[key]}, "
    timings = ""
    for key in timings_fmt.keys():
        timings += f"{key} {timings_fmt[key]}, "
    processes = ""
    for key in processes_fmt.keys():
        processes += f"{key} {processes_fmt[key]}, "
    create_big_db = f"CREATE TABLE big_table ({big_table[:-2]});"
    create_monitoring_db = f"CREATE TABLE monitoring ({monitoring[:-2]});"
    create_timing_db = f"CREATE TABLE timings ({timings[:-2]})"
    create_processes_db = f"CREATE TABLE processes ({processes[:-2]})"

    # Execute the statements generated above and set up headers for the tables
    database = connect(out)  
    database.execute(create_big_db)
    database.execute(create_monitoring_db)
    database.execute(create_timing_db)
    database.execute(create_processes_db)
    database.commit()
    return database


"""
Write the given data in json to the big_table table in the given database
"""
def write_big_table_data(data: json, db: Connection):
    insert = f"INSERT INTO big_table VALUES ({ ('?,' * len(big_table_fmt))[:-1]})"
    db.execute(insert, data)
    db.commit()

"""
Write the given data in json to the timing table in the given database
"""
def write_timing_data(data: json, db: Connection):
    insert = f"INSERT INTO timings VALUES ({ ('?,' * len(timings_fmt))[:-1]})"
    # if data does not include a key from the timing table header, eg: data does not include "server"
    # write an empty string to the key as a placeholder, eg: "server": "";
    data_tuple = tuple([data[key] if key in data else "" for key in timings_fmt.keys()])
    db.execute(insert, data_tuple)
    db.commit()

"""
Given the name of the database, we first make an connection/reference to the database,
then write the given data in json to the monitoring table of that database
"""
def write_monitoring_data(data_tuple: tuple, output_database_name: str):
    insert = f"INSERT INTO monitoring VALUES ({ ('?,' * len(monitoring_fmt))[:-1]})"
    db = setup_data_file_headers(output_database_name)  
    db.execute(insert, data_tuple)
    db.commit()

"""
Given the name of the database, we first make an connection/reference to the database,
then write the given data in json to the processes table of that database
"""
def write_processes_data(data_tuple: tuple, output_database_name: str):
    insert = f"INSERT INTO processes VALUES ({ ('?,' * len(processes_fmt))[:-1]})"
    db = setup_data_file_headers(output_database_name)  
    db.execute(insert, data_tuple)
    db.commit()

"""
Get the current time in terms of year/month/day hour:minute:second
"""
def get_time():
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")
