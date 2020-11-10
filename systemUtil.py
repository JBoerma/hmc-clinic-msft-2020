import psutil
import time 
import signal
import csv
from datetime import datetime
cpuCSVfileName = "result/cpu.csv"
memoryCSVfileName = "result/memory.csv"

def writeData(data, csvFileName: str):
    with open(csvFileName, 'a', newline='\n') as outFile:
        csvWriter = csv.writer(outFile)
        csvWriter.writerow(data)
    print("wrote to {}".format(csvFileName))

def getTime():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# if __name__ == "__main__":
#     start_time = time.time()
#     currentT = 0
#     while True:
#         if (int(round((time.time() - start_time)*1000)))%100 == 0:
#             if run.value == 1:
#                 currentCPUusage.append(psutil.cpu_percent())
#             else:
#                 writeCPUdata(currentCPUusage, cpuCSVfileName)
#                 currentCPUusage = []

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
    currentMemoryUsage = []
    while not killer.kill_now:
        time.sleep(1)
        currentTime.append(getTime())
        currentCPUusage.append(psutil.cpu_percent())
        currentMemoryUsage.append(psutil.virtual_memory().percent)
        print("ideally appending into an array")
    writeData(currentTime, cpuCSVfileName)
    writeData(currentCPUusage, cpuCSVfileName)
    writeData(currentTime, memoryCSVfileName)
    writeData(currentCPUusage, memoryCSVfileName)
    print("ideally writing to csv file")

# utility usauge for a single process
def main(pid):
    killer = GracefulKiller()
    currentCPUusage = []
    currentTime = []
    currentMemoryUsage = []
    p = psutil.Process(pid)
    while not killer.kill_now:
        time.sleep(1)
        currentTime.append(getTime())
        currentCPUusage.append(p.cpu_percent())
        currentMemoryUsage.append(p.memory_percent())
        print("ideally appending into an array")
    writeData(currentTime, cpuCSVfileName)
    writeData(currentCPUusage, cpuCSVfileName)
    writeData(currentTime, memoryCSVfileName)
    writeData(currentCPUusage, memoryCSVfileName)
    print("ideally writing to csv file")