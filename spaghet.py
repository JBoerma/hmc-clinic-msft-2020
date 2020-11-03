from typing import List
import subprocess, csv, json
from playwright import sync_playwright

from args import getArguments

# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"


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

    arguments = getArguments()

    device = arguments.device
    options_list = arguments.options_list
    browsers = arguments.browsers
    reset = RESET_FORMAT.format(DEVICE=device)

    for options in options_list: 
        call  = CALL_FORMAT.format(DEVICE=device, OPTIONS=options)
        
        for browser in browsers:
            name = browser + "_" + options.replace(" ", "_")
            csvFileName = "{}.csv".format(name)

            # Setup data file headers
            with open(csvFileName, 'w', newline='\n') as outFile:
                csvWriter = csv.writer(outFile)
                csvWriter.writerow(timingParameters)

            # run the same experiment 10 times over h3/h2
            with sync_playwright() as p:
                p: "SyncPlaywrightContextManager"

                print("HTTP/3:")
                for _ in range(10):
                    results = runExperiment(call, reset, p, browser, True)
                    writeData(results, csvFileName)

                print("HTTP/2")
                for _ in range(10):
                    results = runExperiment(call, reset, p, browser, False) 
                    writeData(results, csvFileName)

def writeData(data: json, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=timingParameters, extrasaction='ignore')
        csvWriter.writerow(data)

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
    main()