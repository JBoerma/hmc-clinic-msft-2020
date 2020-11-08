"""QUIC Experiment Harness

Usage:
    experiment.py JSON_FILE [options]

Arguments:
    JSON_FILE           JSON file specifying options

Options:
    -h --help           Show this screen 
    --enable_caching    Enables caching
"""
from typing import List
import subprocess, csv, json
import os
from playwright import sync_playwright
from docopt import docopt
import cache_control

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
    # Process args
    args = docopt(__doc__, argv=None, help=True, version=None, options_first=False)
    JSON_FILE=args['JSON_FILE']
    f = open(JSON_FILE,'r')
    options = json.load(f)
    f.close()

    device = options['device']
    options_list = options['options_list']
    browsers = options['browsers']
    url = options['url']
    runs = options['runs']

    if args['--enable_caching']:
        # Assumes that there is no server caching
        cache_control.add_server_caching("/usr/local/nginx/conf/nginx.conf", 23, 9)

    # Make sure server is running
    subprocess.run("sudo systemctl restart nginx.service".split())

    reset = RESET_FORMAT.format(DEVICE=device)

    for options in options_list: 
        call  = CALL_FORMAT.format(DEVICE=device, OPTIONS=options)

        for browser in browsers:
            name = browser + "_" + options.replace(" ", "_")
            directoryPath = "results"
            csvFileName = f"{directoryPath}/{name}.csv"

            # Setup data file headers
            os.makedirs(os.path.dirname(csvFileName), exist_ok=True)
            with open(csvFileName, 'w', newline='\n') as outFile:
                csvWriter = csv.writer(outFile)
                csvWriter.writerow(timingParameters)

            # run the same experiment multiple times over h3/h2
            with sync_playwright() as p:
                p: "SyncPlaywrightContextManager"

                print("HTTP/3:")
                for _ in range(runs):
                    results = runExperiment(call, reset, p, browser, True, url)
                    writeData(results, csvFileName)

                print("HTTP/2:")
                for _ in range(runs):
                    results = runExperiment(call, reset, p, browser, False, url) 
                    writeData(results, csvFileName)

    if args['--enable_caching']:
        # Assumes that there is server caching
        cache_control.remove_server_caching("/usr/local/nginx/conf/nginx.conf", 23)


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

    main()