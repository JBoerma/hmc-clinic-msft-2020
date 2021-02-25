import psutil
import time 
import signal
import csv
import os
import numpy
import json
import sys
import subprocess

from experiment_utils import write_monitoring_data, get_time, write_processes_data

systemUtilLog = "results/systemUtilLog.csv"
hz = os.sysconf('SC_CLK_TCK')

def writeData(data, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.writer(outFile)
        for row in data:
            csvWriter.writerow(row)
    print("wrote to {}".format(csvFileName))


def getDataFromKernel():
    procs = os.listdir('/proc')
    procsCPU = []
    ioWait = []
    procsList = []
    # iterate through all the running process
    for proc in procs:
        if proc.isnumeric():
            try:
                with open('/proc/'+proc+'/stat', 'r') as f:
                    data = f.read()
                stat = data.split()
                # find the process corresponding to the browser instances
                if str(stat[1]) in ['(firefox)', '(chrome)', '(msedge)']:
                    # add the CPU time to the list
                    procsCPU.append(int(stat[13])/hz)
                    # procsMemory.append(stat[22])
                    procsList.append(stat[1][1:-1])
            except FileNotFoundError:
                pass
    with open('/proc/stat', 'r') as f:
        data = f.read()
        for _ in range(len(procsList)):
            # Time waiting for I/O to complete
            currentReading = data.split()[4]
            ioWait.append(currentReading)
    return procsList, procsCPU, ioWait



# https://stackoverflow.com/questions/18499497/how-to-process-sigterm-signal-gracefully
class GracefulKiller:
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True

def collectProcessesData():
    ps = subprocess.check_output(['ps', 'aux']).strip().decode('utf-8').replace("'","")
    processes = ps.split('\n')
    nfields = len(processes[0].split()) - 1
    data = []
    for row in processes[1:]:
        data.append(tuple([int(time.time())] + row.split(None, nfields)))
    return data
        
# general system information
if __name__ == "__main__":
    experimentID = sys.argv[1]
    killer = GracefulKiller()
    # currentcpuTime = []
    # currentTime = []
    # currentIOwait = []
    # currentProcNames = []
    # currentUnixTime = []
    # currentLoad1 = []
    # currentLoad5 = []
    # currentLoad15 = []
    with open('/proc/stat', 'r') as f:
        data = f.read()
    # Time waiting for I/O to complete
    lastReading = data.split()[4]
    # Write processdata
    process_data = collectProcessesData()
    for row in process_data:
        write_processes_data(row)
    while not killer.kill_now:
        time.sleep(1)
        # get a lists of browsers processes and the coresponding cpu and iowait
        procsList, procsCPU, ioWait = getDataFromKernel()
        load1, load5, load15 = os.getloadavg()
        row_tuple = (experimentID, get_time(),int(time.time()),str(procsList), \
            str(procsCPU), str(ioWait), load1, load5, load15) # need to turn lsits into strs
        write_monitoring_data(row_tuple)
