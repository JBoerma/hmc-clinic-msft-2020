import subprocess, json, csv, os
from sqlite3 import Connection, connect
from datetime import datetime
from tqdm import tqdm

option_to_netemParam = {
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

APPLY_LATENCY_LOSS  = "sudo tc qdisc add dev {DEVICE} root handle 1:0 netem delay {LATENCY}ms loss {LOSS}%"
APPLY_LATENCY  = "sudo tc qdisc add dev {DEVICE} root handle 1:0 netem delay {LATENCY}ms"
APPLY_BANDWIDTH  = "sudo tc qdisc add dev {DEVICE} parent 1:1 handle 10: tbf rate {BANDWIDTH}kbps burst {BURST} limit {LIMIT}" #TODO: latency or limit??
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE} root"

def apply_condition(
    device: str, 
    condition: str,
    ):
    latency, loss, bandwidth = option_to_netemParam[condition]
    commandStatus = 0 # run_tc_command(APPLY_BANDWIDTH.format(DEVICE = device, BANDWIDTH = bandwidth, BURST = bandwidth, LIMIT = 2*bandwidth))
    # handeling tc errors
    command = ""
    if loss == 0:
        command = APPLY_LATENCY.format(DEVICE = device, LATENCY = latency)
    else:
        command = APPLY_LATENCY_LOSS.format(DEVICE = device, LATENCY = latency, LOSS = loss)
    commandStatus = run_tc_command(command)
    if commandStatus == 1: # this means that we had some trouble running tc!
        reset_condition(device) # the trouble should be able to be fixed with removing all the previous setting
        tqdm.write("reseting condition")
        retry_command_status = run_tc_command(command)
        if retry_command_status == 0:
            tqdm.write("reset tc command!")
        else:
            tqdm.write("RESET FAILED")
    run_tc_command(APPLY_BANDWIDTH.format(DEVICE = device, BANDWIDTH = bandwidth, BURST = bandwidth, LIMIT = 2*bandwidth))

def reset_condition(
    device: str, 
    ):
    run_tc_command(RESET_FORMAT.format(DEVICE = device))

def run_tc_command(
    command: str,
    
):
    if command:
        tqdm.write(f"commands are {command}")
        result = subprocess.run(command.split())
        if result.returncode > 0:
            tqdm.write("Issue running TC!")
            tqdm.write(str(result.args))
            tqdm.write(str(result.stderr))
            tqdm.write("--------------------------")
            return 1 # failed
        return 0 #success


experiment_parameters = [
    "browser",
    "experimentID",
    "experimentStartTime",
    "netemParams", # TODO: think about better encoding
    "httpVersion", 
    "server",
    "warmup",
]

timing_parameters = [ 
    "startTime",
    # "unloadEventStart",
    # "unloadEventEnd",
    "fetchStart",
    "domainLookupStart",
    "domainLookupEnd",
    "connectStart", 
    "secureConnectionStart",
    "connectEnd", 
    "requestStart", 
    "responseStart", 
    "responseEnd",
    "domInteractive",  
    "domContentLoadedEventStart", 
    "domContentLoadedEventEnd", 
    "domComplete", 
    "loadEventStart",
    "loadEventEnd",
]
parameters = timing_parameters + experiment_parameters

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

out = "results/results.db"


def setup_data_file_headers(
    out: str
):
    if os.path.exists(out):
        return connect(out)
    
    # If directory doesn't exist, can't connect
    # Don't check disk for in-memory database
    if out != ":memory:":
        os.makedirs(os.path.dirname(out),exist_ok = True)

    # only if database doesn't exist 
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
    database = connect(out)  
    database.execute(create_big_db)
    database.execute(create_monitoring_db)
    database.execute(create_timing_db)
    database.execute(create_processes_db)
    database.commit()
    return database


def write_data(data: json, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=parameters, extrasaction='ignore')
        csvWriter.writerow(data)


def write_big_table_data(data: json, db: Connection):
    insert = f"INSERT INTO big_table VALUES ({ ('?,' * len(big_table_fmt))[:-1]})"
    db.execute(insert, data)
    db.commit()


def write_timing_data(data: json, db: Connection):
    insert = f"INSERT INTO timings VALUES ({ ('?,' * len(timings_fmt))[:-1]})"
    data_tuple = tuple([data[key] if key in data else "" for key in timings_fmt.keys()])
    db.execute(insert, data_tuple)
    db.commit()

def write_monitoring_data(data_tuple: tuple):
    insert = f"INSERT INTO monitoring VALUES ({ ('?,' * len(monitoring_fmt))[:-1]})"
    db = setup_data_file_headers(out)  
    db.execute(insert, data_tuple)
    db.commit()

def write_processes_data(data_tuple: tuple):
    insert = f"INSERT INTO processes VALUES ({ ('?,' * len(processes_fmt))[:-1]})"
    db = setup_data_file_headers(out)  
    db.execute(insert, data_tuple)
    db.commit()

def get_time():
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")
