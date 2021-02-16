import psutil
import time 
import signal
import csv
import os
import numpy
import json
import sys

from experiment_utils import write_monitoring_data, get_time

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
                if stat[1] == '(firefox)' or stat[1] == '(chromium)' or stat[1] == '(edge)':
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

# general system information
if __name__ == "__main__":
    experimentID = sys.argv[1]
    killer = GracefulKiller()
    currentCPUusage = []
    currentTime = []
    currentIOwait = []
    currentProcNames = []
    currentUnixTime = []
    with open('/proc/stat', 'r') as f:
        data = f.read()
    # Time waiting for I/O to complete
    lastReading = data.split()[4]

    while not killer.kill_now:
        time.sleep(1)
        procsList, procsCPU, ioWait = getDataFromKernel()
        for i in range(len(procsList)):
            currentTime.append(get_time())
            currentUnixTime.append(int(time.time()))
        currentCPUusage+=procsCPU
        currentIOwait += ioWait
        currentProcNames+=procsList
        # print("ideally appending into an array")
    # compute the differences of iotimes
    # TODO: this will be an issue when we parallize browsers, because 
    # iotime manually matches the processes column. So if we have multiple
    # processes at a time, our iowait will be [actual iowait, 0, 0, ...] 
    # print(currentIOwait)
    # currentIOwait = numpy.array(currentIOwait, dtype=numpy.int64)
    # print(currentIOwait)
    # currentIOwaitDiff = numpy.diff(currentIOwait)
    # print(currentIOwaitDiff)
    zipall = zip(currentTime, currentUnixTime, currentProcNames, currentCPUusage, currentIOwait)
    for row in zipall:
        row_tuple = tuple([experimentID] + list(row))
        # print(row_tuple)
        write_monitoring_data(row_tuple)
    writeData(zipall, systemUtilLog)
    print("ideally writing to csv file")
