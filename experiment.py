from typing import List
import subprocess, csv, json
import os
from playwright import sync_playwright
<<<<<<< HEAD:experiment.py
import time
import random

from args import getArguments

=======
import multiprocessing as mp
import psutil
import time
>>>>>>> add initial cpu measurement:spaghet.py

# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"

experimentParameters = [
    "experimentID",
    "netemParams", # TODO: think about better encoding
    "httpVersion", 
]
timingParameters = [ 
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
parameters = experimentParameters + timingParameters

def process1(process2Run):   
    # Make sure server is running
    subprocess.run("sudo systemctl restart nginx.service".split())

<<<<<<< HEAD:experiment.py
    arguments = getArguments()

    device = arguments.device
    options_list = arguments.options_list
    browsers = arguments.browsers
    url = arguments.url
    runs = arguments.runs

    reset = RESET_FORMAT.format(DEVICE=device)

    for options in options_list: 
        call  = CALL_FORMAT.format(DEVICE=device, OPTIONS=options)
        experimentID = int(time.time()) # ensures no repeats
        netemParams = options
        
        for browser in browsers:
            name = browser + "_" + options.replace(" ", "_")
            directoryPath = "results"
            csvFileName = f"{directoryPath}/{name}.csv"

            # Setup data file headers
            os.makedirs(os.path.dirname(csvFileName), exist_ok=True)
            with open(csvFileName, 'w', newline='\n') as outFile:
                csvWriter = csv.writer(outFile)
                csvWriter.writerow(parameters)
            
            whenRunH3 = runs * [True] + runs * [False]
            random.shuffle(whenRunH3)

            # run the same experiment multiple times over h3/h2
            with sync_playwright() as p:
                for useH3 in whenRunH3:
                    results = runExperiment(call, reset, p, browser, useH3, url)
                    results["experimentID"] = experimentID
                    results["netemParams"] = netemParams
                    results["httpVersion"] = "h3" if useH3 else "h2"
                    writeData(results, csvFileName)
=======
        print("HTTP/3:")
        for _ in range(10):
            # signal process2 to collect cpu data
            process2Run.value = 1
            results = runExperiment(call, reset, p, "firefox", True)
            # signal process2 to stop collecting cpu data
            process2Run.value = 2
            writeData(results, csvFileName)

        print("HTTP/2")
        for _ in range(10):
            # signal process2 to collect cpu data
            process2Run.value = 1
            results = runExperiment(call, reset, p, "firefox", False) 
            # signal process2 to stop collecting cpu data
            process2Run.value = 2
            writeData(results, csvFileName)
    

def process2(run):
    currentCPUusage = []
    cpuCSVfileName = "cpu.csv"
    start_time = time.time()
    currentT = 0
    while True:
        if (int(round((time.time() - start_time)*1000)))%10 == 0:
            if run.value == 1:
                currentCPUusage.append(psutil.cpu_percent())
            else:
                writeCPUdata(currentCPUusage, cpuCSVfileName)
                currentCPUusage = []
>>>>>>> add initial cpu measurement:spaghet.py

def writeData(data: json, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=parameters, extrasaction='ignore')
        csvWriter.writerow(data)

def writeCPUdata(data, csvFileName: str):
    with open(csvFileName, 'w+', newline='\n') as outFile:
        csvWriter = csv.writer(outFile)
        csvWriter.writerow(data)
    print("wrote to cpu.csv")

def launchBrowser(
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str,
    url: str, 
    h3: bool,
) -> json:
    if browserType  ==  "firefox":
        return launchFirefox(pwInstance, url, h3)
    elif browserType  ==  "chromium":
        return launchChromium(pwInstance, url, h3)
    elif browserType  ==  "edge":
        return launchEdge(pwInstance, url, h3)

def launchFirefox(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
) -> json:
    firefoxPrefs = {"privacy.reduceTimerPrecision":False}
    if (h3):
        domain = url if "https://" not in url else url[8:]
        firefoxPrefs = {
            "network.http.http3.enabled":True,
            "network.http.http3.alt-svc-mapping-for-testing":f"{domain};h3-29=:443",
            "privacy.reduceTimerPrecision":False
        }
    browser = pwInstance.firefox.launch(
        headless=True,
        firefoxUserPrefs=firefoxPrefs,
    )

    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url)
    print("Firefox: ",response.headers['version'])

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))

    browser.close()
    return performanceTiming

def launchChromium(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
) -> json:
    chromiumArgs = []
    if (h3):
        domain = url if "https://" not in url else url[8:]
        chromiumArgs = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]

    browser =  pwInstance.chromium.launch(
        headless=True,
        args=chromiumArgs,
    )
    context = browser.newContext()
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url)
    print("Chromium: ",response.headers['version'])

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))
    
    browser.close()
    return performanceTiming

def launchEdge(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
) -> json:
    edgeArgs = []
    if (h3) :
        domain = url if "https://" not in url else url[8:]
        edgeArgs = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
    browser = pwInstance.chromium.launch(
        headless=True,
        executablePath='/opt/microsoft/msedge-dev/msedge',
        args=edgeArgs,
    )
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url)
    print("Edge: ",response.headers['version'])

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))
    
    browser.close()
    return performanceTiming
    
def runExperiment(
    call: str, 
    reset: str, 
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str, 
    h3: bool,
    url: str,
) -> json:
    runTcCommand(call)
    results = launchBrowser(pwInstance, browserType, url, h3)
    runTcCommand(reset)

    return results


def runTcCommand(
    command: str,
):
    result = subprocess.run(command.split())
    if result.returncode > 0:
        print("Issue running TC!")
        print(result.args)
        print(result.stderr)
        print("--------------------------")

if __name__ == "__main__":
    process2Run = mp.Value("i", 1)
    process2Stop = mp.Value("b", True)
    p = mp.Process(target=process1, args=(process2Run,))
    p.start()
    p2 = mp.Process(target=process2, args = (process2Run,))
    p2.start()
    p.join()
    p2.join()