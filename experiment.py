"""QUIC Experiment Harness

Usage:
    experiment.py experiment.py [--device DEVICE] [--options OPTIONS] [--browsers BROWSERS] [--url URL] [--runs RUNS] [options]
    
Arguments:
    --device DEVICE           Network device to modify [default: lo root]
    --options OPTIONS         tc-netem conditions to apply [default: delay 0ms]
    --browsers BROWSERS       List of browsers to test [default: firefox,chromium,edge]
    --url URL                 URL to access [default: https://localhost]
    --runs RUNS               Number of runs in the experiment [default: 1]

Options:
    -h --help                 Show this screen 
    --disable_caching         Disables caching
    --warmup                  Warms up connection
"""
from typing import List
import subprocess, csv, json
import os
from playwright import sync_playwright
from docopt import docopt
import cache_control
import time
import random

from args import getArguments


# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"

experimentParameters = [
    "experimentID",
    "netemParams", # TODO: think about better encoding
    "httpVersion", 
    "warmup",
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

def main():   
    # Process args
    args = docopt(__doc__, argv=None, help=True, version=None, options_first=False)
    device = args['--device']
    options = args['--options']
    browsers = args['--browsers'].split(",")
    url = args['--url']
    runs = int(args['--runs'])

    disable_caching = args['--disable_caching']
    warmup_connection = args['--warmup']

    server_conf = "/usr/local/nginx/conf/nginx.conf"
    
    if disable_caching:
        # Assumes that there is server caching by default
        cache_control.remove_server_caching(server_conf, 23)
    # Make sure server is running
    subprocess.run("sudo systemctl restart nginx.service".split())

    reset = RESET_FORMAT.format(DEVICE=device)

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
                results = runExperiment(call, reset, p, browser, useH3, url, warmup=warmup_connection)
                results["experimentID"] = experimentID
                results["netemParams"] = netemParams
                results["httpVersion"] = "h3" if useH3 else "h2"
                results["warmup"] = warmup_connection
                writeData(results, csvFileName)

    if disable_caching:
        # Re-enable server caching
        cache_control.add_server_caching(server_conf, 23, 9)

def writeData(data: json, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=parameters, extrasaction='ignore')
        csvWriter.writerow(data)

def warmupIfSpecified(
    playwrightPage: "Page",
    url: str,
    warmup: bool,
) -> None: 
    if warmup:
        playwrightPage.goto(url)

def launchBrowser(
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str,
    url: str, 
    h3: bool,
    warmup: bool,
) -> json:
    if browserType  ==  "firefox":
        return launchFirefox(pwInstance, url, h3, warmup)
    elif browserType  ==  "chromium":
        return launchChromium(pwInstance, url, h3, warmup)
    elif browserType  ==  "edge":
        return launchEdge(pwInstance, url, h3, warmup)

def launchFirefox(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    warmup: bool,
) -> json:
    firefoxPrefs = {}
    firefoxPrefs["privacy.reduceTimerPrecision"] = False
    
    if h3:
        domain = url if "https://" not in url else url[8:]
        firefoxPrefs["network.http.http3.enabled"] = True
        firefoxPrefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-29=:443"

    if warmup:
        firefoxPrefs["devtools.cache.disabled"] = True

    browser = pwInstance.firefox.launch(
        headless=True,
        firefoxUserPrefs=firefoxPrefs,
    )
    context = browser.newContext()
    page = context.newPage()
    warmupIfSpecified(page, url, warmup)
    response = page.goto(url)
    print("Firefox: ", response.headers['version'])

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
    warmup: bool,
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
    warmupIfSpecified(page, url, warmup)
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
    warmup: bool,
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
    warmupIfSpecified(page, url, warmup)
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
    warmup: bool,
) -> json:
    runTcCommand(call)
    results = launchBrowser(pwInstance, browserType, url, h3, True)
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
