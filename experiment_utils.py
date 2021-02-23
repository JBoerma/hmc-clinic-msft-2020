import subprocess, json, csv, os
from sqlite3 import Connection, connect

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

APPLY_LATENCY_LOSS  = "sudo tc qdisc add dev {DEVICE} parent 1:1 handle 10: netem delay {LATENCY}ms loss {LOSS}%"
APPLY_BANDWIDTH  = "sudo tc qdisc add dev {DEVICE} root handle 1: tbf rate {BANDWIDTH}kbps burst {BURST}k limit {LIMIT}k" #TODO: this can be wrong
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE} root"

def apply_condition(
    device: str, 
    condition: str,
    ):
    latency, loss, bandwidth = option_to_netemParam[condition]
    run_tc_command(APPLY_BANDWIDTH.format(DEVICE = device, BANDWIDTH = bandwidth, BURST = int(bandwidth/1000), LIMIT = int(2*bandwidth/1000)))
    run_tc_command(APPLY_LATENCY_LOSS.format(DEVICE = device, LATENCY = latency, LOSS = loss))


def reset_condition(
    device: str, 
    ):
    run_tc_command(RESET_FORMAT.format(DEVICE = device))

def run_tc_command(
    command: str,
):
    if command:
        print("commands are", command)
        result = subprocess.run(command.split())
        if result.returncode > 0:
            print("Issue running TC!")
            print(result.args)
            print(result.stderr)
            print("--------------------------")


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

cpu_usage_fmt = {
    "experimentID" : "TEXT",
    "cpuUsage" : "TEXT",
    "ioUsage" : "TEXT",
    "unixTime" : "INT"
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
}


def setup_data_file_headers(
    out: str
):
    if os.path.exists(out):
        return connect(out)

    # only if database doesn't exist 
    big_table = ""
    for key in big_table_fmt.keys():
        big_table += f"{key} {big_table_fmt[key]}, "
    cpu_time = ""
    for key in cpu_usage_fmt.keys():
        cpu_time += f"{key} {cpu_usage_fmt[key]}, "
    timings = ""
    for key in timings_fmt.keys():
        timings += f"{key} {timings_fmt[key]}, "
    create_big_db = f"CREATE TABLE big_table ({big_table[:-2]});"
    create_cpu_db = f"CREATE TABLE cpu_time ({cpu_time[:-2]});"
    create_timing_db = f"CREATE TABLE timings ({timings[:-2]})"
    database = connect(out)  
    database.execute(create_big_db)
    database.execute(create_cpu_db)
    database.execute(create_timing_db)
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
    data_tuple = tuple([data[key] for key in timings_fmt.keys()])
    db.execute(insert, data_tuple)
    db.commit()