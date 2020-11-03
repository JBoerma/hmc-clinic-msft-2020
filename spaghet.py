import subprocess, csv, json
from playwright import sync_playwright

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

def main():   
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
            runExperiment(call, reset, p, "firefox", csvFileName, True)

        print("HTTP/2")
        for _ in range(10):
            runExperiment(call, reset, p, "firefox", csvFileName, False) 

def writeData(data: json, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=timingParameters, extrasaction='ignore')
        csvWriter.writerow(data)

def launchBrowser(
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str,
    csvFileName: str, 
    url: str, 
    h3: bool,
):
    if browserType  ==  "firefox":
        launchFirefox(pwInstance, csvFileName, url, h3)
    elif browserType  ==  "chromium":
        launchChromium(pwInstance, csvFileName, url, h3)
    elif browserType  ==  "edge":
        launchEdge(pwInstance, csvFileName, url, h3)

def launchFirefox(
    pwInstance: "SyncPlaywrightContextManager", 
    csvFileName: str, 
    url: str, 
    h3: bool,
):
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

    writeData(performanceTiming, csvFileName)
    browser.close()

def launchChromium(
    pwInstance: "SyncPlaywrightContextManager", 
    csvFileName: str, 
    url: str, 
    h3: bool,
):
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
    
    writeData(performanceTiming, csvFileName)
    browser.close()

def launchEdge(
    pwInstance: "SyncPlaywrightContextManager", 
    csvFileName: str, 
    url: str, 
    h3: bool,
):
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
    
    writeData(performanceTiming, csvFileName)
    browser.close()
    
def runExperiment(
    call: str, 
    reset: str, 
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str, 
    csvFileName: str, 
    h3: bool,
):
    url = "https://localhost"

    runTcCommand(call)
    launchBrowser(pwInstance, browserType, csvFileName, url, h3)
    runTcCommand(reset)


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
    main()