import psutil
import time 
import signal
import csv
from getTime import getTime
import os
cpuCSVfileName = "results/cpu.csv"
memoryCSVfileName = "results/memory.csv"
systemUtilLog = "results/systemUtilLog.csv"
hz = os.sysconf('SC_CLK_TCK')
def writeData(data, csvFileName: str):
    with open(csvFileName, 'a', newline='\n') as outFile:
        csvWriter = csv.writer(outFile)
        for row in data:
            csvWriter.writerow(row)
    print("wrote to {}".format(csvFileName))

def getDataFromPsutil():
    procsCPU = []
    procsMemory = []
    procsList = []
    for proc in psutil.process_iter():
        if proc.name() == 'firefox' or proc.name() == '(chromium)' or proc.name()  == '(edge)':
            procsCPU.append(proc.cpu_percent())
            procsMemory.append(proc.memory_percent())
            procsList.append(proc.name())
    return procsList, procsCPU, procsMemory

def getDataFromKernal():
    procs = os.listdir('/proc')
    procsCPU = []
    ioWait = []
    procsList = []
    # iterate through all the running process
    for proc in procs:
        if proc.isnumeric():
            with open('/proc/'+proc+'/stat', 'r') as f:
                data = f.read()
            stat = data.split()
            # find the process corresponding to the browser instances
            if stat[1] == '(firefox)' or stat[1] == '(chromium)' or stat[1] == '(edge)':
                # add the CPU time to the list
                procsCPU.append(int(stat[13])/hz)
                # procsMemory.append(stat[22])
                procsList.append(stat[1])
    with open('/proc/stat', 'r') as f:
        data = f.read()
        for _ in range(len(procsList)):
            # Time waiting for I/O to complete
            ioWait.append(data.split()[4])
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
    
    killer = GracefulKiller()
    currentCPUusage = []
    currentTime = []
    currentIOwait = []
    currentProcNames = []
    while not killer.kill_now:
        time.sleep(1)
        # getDataFromPsutil()
        procsList, procsCPU, ioWait = getDataFromKernal()
        for i in range(len(procsList)):
            currentTime.append(getTime())
        currentCPUusage+=procsCPU
        currentIOwait += ioWait
        currentProcNames+=procsList
        # currentCPUusage.append(psutil.cpu_percent())
        # currentMemoryUsage.append(psutil.virtual_memory().percent)
        print("ideally appending into an array")
    zipall = zip(currentTime, currentProcNames, currentCPUusage, currentIOwait)
    writeData(zipall, systemUtilLog)
    print("ideally writing to csv file")
