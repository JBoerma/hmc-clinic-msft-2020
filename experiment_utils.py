import subprocess, json, csv, os
from sqlite3 import Connection, connect
from datetime import datetime


def run_tc_command(
    command: str,
):
    if command:
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
    "netemParams" : "TEXT"
    }

monitoring_fmt = {
    "experimentID" : "TEXT",
    "currentTime" : "TEXT",
    "unixTime" : "INT",
    "currentProcNames" : "TEXT",
    "cpuUsage" : "TEXT",
    "ioWait" : "INT"
    }

timings_fmt = {
    "experimentID" : "TEXT",
    "browser" : "TEXT",
    "server" : "TEXT",
    "httpVersion" : "TEXT",
    "warmup" : "BOOL",
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

out = "results/results.db"


def setup_data_file_headers(
    out: str
):
    if os.path.exists(out):
        return connect(out)

    # only if database doesn't exist 
    big_table = ""
    for key in big_table_fmt.keys():
        big_table += f"{key} {big_table_fmt[key]}, "
    monitoring = ""
    for key in monitoring_fmt.keys():
        monitoring += f"{key} {monitoring_fmt[key]}, "
    print(monitoring)
    timings = ""
    for key in timings_fmt.keys():
        timings += f"{key} {timings_fmt[key]}, "
    create_big_db = f"CREATE TABLE big_table ({big_table[:-2]});"
    create_monitoring_db = f"CREATE TABLE monitoring ({monitoring[:-2]});"
    create_timing_db = f"CREATE TABLE timings ({timings[:-2]})"
    database = connect(out)  
    database.execute(create_big_db)
    database.execute(create_monitoring_db)
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

def write_monitoring_data(data_tuple: tuple):
    insert = f"INSERT INTO monitoring VALUES ({ ('?,' * len(monitoring_fmt))[:-1]})"
    db = setup_data_file_headers(out)  
    db.execute(insert, data_tuple)
    db.commit()

def get_time():
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")