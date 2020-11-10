import subprocess, csv, json
from playwright import sync_playwright
import multiprocessing as mp
import psutil
import time

# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"

call  = CALL_FORMAT.format(DEVICE="lo root", OPTIONS="delay 100ms 10ms 25%")
reset = RESET_FORMAT.format(DEVICE="lo root")


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

def process1(process2Run):   
    # Make sure server is running
    subprocess.run("sudo systemctl restart nginx.service".split())
    
    csvFileName = "out.csv"

    # Setup data file headers
    with open(csvFileName, 'w', newline='\n') as outFile:
        csvWriter = csv.writer(outFile)
        csvWriter.writerow(timingParameters)

    # run the same experiment 10 times over h3/h2
    with sync_playwright() as p:
        p: "SyncPlaywrightContextManager"

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

def writeData(data: json, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=timingParameters, extrasaction='ignore')
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
    firefoxPrefs = {}
    if (h3):
        firefoxPrefs = {
            "network.http.http3.enabled":True,
            "network.http.http3.alt-svc-mapping-for-testing":"localhost;h3-29=:443",
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
        chromiumArgs = ["--enable-quic", "--origin-to-force-quic-on=localhost:443", "--quic-version=h3-29"]

    browser =  pwInstance.chromium.launch(
        headless=True,
        args=chromiumArgs,
    )
    context = browser.newContext()
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url)
    print("Chromium: ",response.headers()['version'])

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
        edgeArgs = ["--enable-quic", "--origin-to-force-quic-on=localhost:443", "--quic-version=h3-29"]
    browser = pwInstance.chromium.launch(
        headless=True,
        executablePath='/opt/microsoft/msedge-dev/msedge',
        args=edgeArgs,
    )
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url)
    print("Edge: ",response.headers()['version'])

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
) -> json:
    url = "https://localhost"

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