import psutil

def collectCPUdata():
    while True:
        print(psutil.cpu_percent())