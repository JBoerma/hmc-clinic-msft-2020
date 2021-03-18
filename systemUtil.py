import psutil
import time 
import signal
import csv
import os
import sys
import subprocess
from experiment_utils import write_monitoring_data, get_time, write_processes_data

import logging
logger = logging.getLogger()

systemUtilLog = "results/systemUtilLog.csv"
hz = os.sysconf('SC_CLK_TCK')

"""
Return data about browser processes (the client) in two lists and a float
broswers_names: a list of the names of the processes (browser type: firefox, edge, chromium)
broswers_cpu_times: a list of the corresponding CPU time
broswers_iowait: the current iowait
"""
def get_broswer_util_data():
    procs = os.listdir('/proc')
    procs_cpu_times = []
    procs_names = []

    # Determine if we're monitoring client or server
    if sys.argv[2] == 'client':
        procs_checklist = ['(firefox)', '(chrome)', '(msedge)']
    elif sys.argv[2] == 'server':
        procs_checklist = ['(nginx)','(caddy)','(openlitespeed)']

    # iterate through all the running process with numeric pid
    for proc in procs:
        if proc.isnumeric():
            try:
                # get the status information about the process
                # https://man7.org/linux/man-pages/man5/procfs.5.html 
                with open('/proc/'+proc+'/stat', 'r') as f:
                    data = f.read()
                stat = data.split()
                # find the process corresponding to the browser instances
                # proc/[pid]/stat[1]:comm is the filename of the executable 
                if str(stat[1]) in procs_checklist:
                    # add the CPU time to the list
                    # proc/[pid]/stat[13]:utime is the amount of time that this process has been scheduled
                    # in user mode, measured in clock ticks 
                    procs_cpu_times.append(int(stat[13])/hz)
                    # add the name of the process (browser instance) to the list
                    procs_names.append(stat[1][1:-1])
            # sometimes right after we obtain the pid, the process ends, then we will ignore the process
            except FileNotFoundError:
                pass
    # Get iowait data
    with open('/proc/stat', 'r') as f:
        data = f.read()
        # proc/stat[4]: iowait is the time  a task waits for I/O to complete
        # this number is not reliable, detailed see https://man7.org/linux/man-pages/man5/procfs.5.html
        iowait = data.split()[4]
    return procs_names, procs_cpu_times, iowait


"""
In experiment.py run_sync_experiment, we will start a process running systemUtil.py
to start monitoring the system, and we will also kill the process running systemUtil.py.
This class is crucial to process SIGERM signal gracefully. Reference:
https://stackoverflow.com/questions/18499497/how-to-process-sigterm-signal-gracefully
"""
class GracefulKiller:
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True

"""
Return data of all running processes, collected from the command `ps aux`
as a list of tuples of information about processes
"""
def get_all_processes_data():
    ps = subprocess.check_output(['ps', 'aux']).strip().decode('utf-8').replace("'","")
    processes = ps.split('\n')
    nfields = len(processes[0].split()) - 1
    data = []
    for row in processes[1:]:
        data.append(tuple([int(time.time())] + row.split(None, nfields)))
    return data
        

if __name__ == "__main__":
    # getting experimentID and database name from the arguments
    experimentID = sys.argv[1]
    output_database_name = sys.argv[3]
    killer = GracefulKiller()
    # Write processdata to the database TODO how often should we write process data to the database?
    process_data = get_all_processes_data()
    for row in process_data:
        write_processes_data(row, output_database_name)
    # every sec, collect browsers information
    while not killer.kill_now:
        time.sleep(1)
        # get a lists of browsers processes and the coresponding cpu time and iowait
        procs_names, procs_cpu_times, procs_iowait = get_broswer_util_data()
        # get the load average in 1 min, 5 mins, and 15 mins
        load1, load5, load15 = os.getloadavg()
        row_tuple = (experimentID, get_time(),int(time.time()),str(procs_names), \
            str(procs_cpu_times), procs_iowait, load1, load5, load15) # need to turn lsits into strs
        write_monitoring_data(row_tuple, output_database_name)
