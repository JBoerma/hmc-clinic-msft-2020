"""QUIC Experiment Harness

Usage:
    experiment.py experiment.py [--device DEVICE] [--options OPTIONS ...] [--browsers BROWSERS ...] [--url URL] [--runs RUNS] [options] 
    
Arguments:
    --device DEVICE           Network device to modify [default: lo root]
    --options OPTIONS         tc-netem conditions to apply [default: delay 0ms]
    --browsers BROWSERS       List of browsers to test [default: firefox chromium edge]
    --url URL                 URL to access [default: https://localhost]
    --runs RUNS               Number of runs in the experiment [default: 1]

Options:
    -h --help                 Show this screen 
    --disable_caching         Disables caching
    --multi-server            Uses all four server ports
"""
import os, cache_control, time, random, subprocess, csv, json
from typing import List
from playwright import sync_playwright
from docopt import docopt
from args import getArguments
from tqdm import tqdm


# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"

experimentParameters = [
    "experimentID",
    "netemParams", # TODO: think about better encoding
    "httpVersion", 
    "server"
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
    # Fix docopt splitting default argument
    if options == ["delay", "0ms"]:
        options = ["delay 0ms"]
    browsers = args['--browsers']
    url = args['--url']
    runs = int(args['--runs'])
    server_conf = "/usr/local/nginx/conf/nginx.conf"

    if args['--disable_caching']:
        # Assumes that there is server caching by default
        cache_control.remove_server_caching(server_conf, 23)
    # Make sure server is running
    subprocess.run("sudo systemctl restart nginx.service".split())
    with sync_playwright() as p:
        for netemParams in tqdm(options, desc="Experiments"):
            reset = RESET_FORMAT.format(DEVICE=device)

            call  = CALL_FORMAT.format(DEVICE=device, OPTIONS=netemParams)
            experimentID = int(time.time()) # ensures no repeats
            for browser in tqdm(browsers, f"Browsers for '{netemParams}'"):
                name = browser + "_" + netemParams.replace(" ", "_")
                directoryPath = "results"
                csvFileName = f"{directoryPath}/{name}.csv"

                # Setup data file headers
                os.makedirs(os.path.dirname(csvFileName), exist_ok=True)
                with open(csvFileName, 'w', newline='\n') as outFile:
                    csvWriter = csv.writer(outFile)
                    csvWriter.writerow(parameters)
                
                whenRunH3 = runs * [True] + runs * [False]
                random.shuffle(whenRunH3)
                perServer = runs // 4
                # Ensure all servers are represented the same amount in H2 vs. H3
                if runs < 4 or not args['--multi-server']:
                    whichServer = [':443'] * (runs * 2)
                else:
                    servers1 = [':443', ':444', ':445', ':7080/login.php?logoff=1'] * perServer
                    servers2 = [':443', ':444', ':445', ':7080/login.php?logoff=1'] * perServer
                    random.shuffle(servers1)
                    random.shuffle(servers2)
                    whichServer = servers1 + servers2
                # run the same experiment multiple times over h3/h2
                for useH3 in tqdm(whenRunH3, desc=f"Runs for {browser}"):
                    results = runExperiment(call, reset, p, browser, useH3, url, whichServer.pop())
                    results["experimentID"] = experimentID
                    results["netemParams"] = netemParams
                    results["httpVersion"] = "h3" if useH3 else "h2"
                    writeData(results, csvFileName)
                    httpVersion = "HTTP/3" if useH3 else "HTTP/2"
                    # Print info from latest run and then go back lines to prevent broken progress bars
                    tqdm.write(f"\033[F\033[K{browser}: {results['server']} ({httpVersion})       ")
                print("", end="\033[F\033[K")
            print("", end="\033[F\033[K")
    if args['--disable_caching']:
        # Re-enable server caching
        cache_control.add_server_caching(server_conf, 23, 9)
    print("Finished!\n")


def writeData(data: json, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=parameters, extrasaction='ignore')
        csvWriter.writerow(data)

def launchBrowser(
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str,
    url: str, 
    h3: bool,
    port: str
) -> json:
    if browserType  ==  "firefox":
        return launchFirefox(pwInstance, url, h3, port)
    elif browserType  ==  "chromium":
        return launchChromium(pwInstance, url, h3, port)
    elif browserType  ==  "edge":
        return launchEdge(pwInstance, url, h3, port)

def launchFirefox(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str
) -> json:
    firefoxPrefs = {"privacy.reduceTimerPrecision":False}
    if (h3):
        domain = url if "https://" not in url else url[8:]
        firefoxPrefs = {
            "network.http.http3.enabled":True,
            "network.http.http3.alt-svc-mapping-for-testing":f"{domain};h3-29={port.split('/')[0]}",
            "privacy.reduceTimerPrecision":False
        }
    browser = pwInstance.firefox.launch(
        headless=True,
        firefoxUserPrefs=firefoxPrefs,
    )
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url + port)

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))
    performanceTiming['server'] = response.headers['server']

    browser.close()
    return performanceTiming

def launchChromium(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str
) -> json:
    chromiumArgs = []
    if (h3):
        domain = url if "https://" not in url else url[8:]
        chromiumArgs = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]

    try:
        browser =  pwInstance.chromium.launch(
            headless=True,
            args=chromiumArgs,
        )
    except:
        browser =  pwInstance.chromium.launch(
            headless=True,
            args=chromiumArgs,
        )
    context = browser.newContext()
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url + port)

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))
    performanceTiming['server'] = response.headers['server']

    browser.close()
    return performanceTiming

def launchEdge(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str
) -> json:
    edgeArgs = []
    if (h3) :
        domain = url if "https://" not in url else url[8:]
        edgeArgs = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
    try:
        browser = pwInstance.chromium.launch(
            headless=True,
            executablePath='/opt/microsoft/msedge-dev/msedge',
            args=edgeArgs,
        )
    except:
        browser = pwInstance.chromium.launch(
            headless=True,
            executablePath='/opt/microsoft/msedge-dev/msedge',
            args=edgeArgs,
        )
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url + port)

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))
    performanceTiming['server'] = response.headers['server']
    
    browser.close()
    return performanceTiming
    
def runExperiment(
    call: str, 
    reset: str, 
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str, 
    h3: bool,
    url: str,
    port: str
) -> json:
    runTcCommand(call)
    results = launchBrowser(pwInstance, browserType, url, h3, port)
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
