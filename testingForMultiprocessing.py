import multiprocessing as mp
import os
import spaghet
import cpuUsage

processes = ("process1", "process2")

def process1():
    # for i in range(10000):
    #     print("process1 ",i)
    spaghet.main()


def process2():
    # for i in range(10000):
    #     print("process2 ",i)
    cpuUsage.collectCPUdata()
    






if __name__ == "__main__":
    p = mp.Process(target=process1)
    p.start()
    # p.join()
    p2 = mp.Process(target=process2)
    p2.start()
    p.join()
    p2.join()

