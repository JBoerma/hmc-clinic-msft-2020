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
    --warmup                  Warms up connection
"""

import os, cache_control, time, random, subprocess, csv, json
from typing import List
from playwright import sync_playwright, helper
from docopt import docopt
from getTime import getTime
from args import getArguments
from tqdm import tqdm
from multiprocessing import Pool

# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"

experimentParameters = [
    "experimentID",
    "experimentStartTime",
    "netemParams", # TODO: think about better encoding
    "httpVersion", 
    "server",
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
    # Fix docopt splitting default argument
    if options == ["delay", "0ms"]:
        options = ["delay 0ms"]
    browsers = args['--browsers']
    url = args['--url']
    runs = int(args['--runs'])

    disable_caching = args['--disable_caching']
    warmup_connection = args['--warmup']

    server_conf = "/usr/local/nginx/conf/nginx.conf"

    if disable_caching:
        # Assumes that there is server caching by default
        try:
            cache_control.remove_server_caching(server_conf, 23)
        except FileNotFoundError:
            print ("!!!!!!!!!!!!!!!!!!!!!!!!!! \n" +
            "Server config not found!!!\n" + "Download https://github.com/JBoerma/hmc-clinic-msft-2020/blob/master/install/nginx.conf to ./usr/local/nginx/conf/nginx.conf")
    # Make sure server is running
    if "localhost" in url or "127.0.0.1" in url:
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
                if not os.path.exists(csvFileName):
                    with open(csvFileName, 'w', newline='\n') as outFile:
                        csvWriter = csv.writer(outFile)
                        csvWriter.writerow(parameters)
                
                whenRunH3 = runs * [True] + runs * [False]
                random.shuffle(whenRunH3)
                perServer = runs // 4
                total_runs = runs *2
                # Ensure all servers are represented the same amount in H2 vs. H3
                if runs < 4 or not args['--multi-server']:
                    whichServer = [':443'] * total_runs
                else:
                    servers1 = [':443', ':444', ':445', ':7080/login.php'] * perServer
                    servers2 = [':443', ':444', ':445', ':7080/login.php'] * perServer
                    random.shuffle(servers1)
                    random.shuffle(servers2)
                    whichServer = servers1 + servers2
                # run the same experiment multiple times over h3/h2
                # for useH3 in tqdm(whenRunH3, desc=f"Runs for {browser}"):
                #     writeExperimentAndWriteData(call, reset,p, browser, useH3, url,whichServer.pop(),warmup_connection,experimentID,netemParams, csvFileName)
                # args_list = [[call,reset,p,browser,whenRunH3[i], url, whichServer[i], warmup_connection, experimentID, netemParams, csvFileName] for i in range(total_runs)]
                args_list = list(zip([call]*total_runs, 
                                [reset]*total_runs, 
                                [p]*total_runs,
                                [browser]*total_runs,
                                whenRunH3, 
                                [url]*total_runs,
                                whichServer,
                                [warmup_connection]*total_runs,
                                [experimentID]*total_runs,
                                [netemParams]*total_runs,
                                [csvFileName]*total_runs))
                # print(args_list)
                with Pool(processes=4) as pool:
                    print(pool.starmap(writeExperimentAndWriteData, args_list)) # TODO: Do not use this!!!
                    # TODO: run this experiments multiple times as the same time is enough!!!
                    # otherwise, use threading, instead of multiprocessing
                print("", end="\033[F\033[K")
            print("", end="\033[F\033[K")
    if args['--disable_caching']:
        # Re-enable server caching
        cache_control.add_server_caching(server_conf, 23, 9)
    print("Finished!\n")

def writeExperimentAndWriteData(
    call, 
    reset,
    p,
    browser,
    useH3,
    url,
    whichServer,
    warmup_connection,
    experimentID,
    netemParams,
    csvFileName):
    try:
        results = runExperiment(call, reset, p, browser, useH3, url, whichServer, warmup=warmup_connection)
        results["experimentID"] = experimentID
        results["netemParams"] = netemParams
        results["httpVersion"] = "h3" if useH3 else "h2"
        results["warmup"] = warmup_connection
        writeData(results, csvFileName)
        httpVersion = "HTTP/3" if useH3 else "HTTP/2"
        # Print info from latest run and then go back lines to prevent broken progress bars
        tqdm.write(f"\033[F\033[K{browser}: {results['server']} ({httpVersion})       ")
        print("here")
    except:
        pass

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
        # "?<random_string>" forces browser to re-request data
        new_url = url + "?send_data_again"
        playwrightPage.goto(new_url)

def launchBrowser(
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    if browserType  ==  "firefox":
        return launchFirefox(pwInstance, url, h3, port, warmup)
    elif browserType  ==  "chromium":
        return launchChromium(pwInstance, url, h3, port, warmup)
    elif browserType  ==  "edge":
        return launchEdge(pwInstance, url, h3, port, warmup)

def launchFirefox(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    firefoxPrefs = {}
    firefoxPrefs["privacy.reduceTimerPrecision"] = False
    
    if h3:
        domain = url if "https://" not in url else url[8:]
        firefoxPrefs["network.http.http3.enabled"] = True
        firefoxPrefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-29={port.split('/')[0]}"
    try:
        browser = pwInstance.firefox.launch(
            headless=True,
            firefoxUserPrefs=firefoxPrefs,
        )
        return getResults(browser, url, h3, port, warmup)
    except:
        print ( "!!!!!!!!!!!!!!!!!!!!!!!!!! \n" +
        "Firefox browser not found!!! \n"+
        "Maybe you want to run \"npm -i playwright-firefox\"")

def launchChromium(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
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
        return getResults(browser, url, h3, port, warmup)
    except:
        print ( "!!!!!!!!!!!!!!!!!!!!!!!!!! \n" +
        "Chromium browser not found!!! \n"+
        "Maybe you want to run \"npm -i playwright-chromium\"")


def launchEdge(
    pwInstance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
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
        return getResults(browser, url, h3, port, warmup)
    except:
        print ( "!!!!!!!!!!!!!!!!!!!!!!!!!! \n" +
        "Edge browser not found!!! \n"+
        "Download at https://www.microsoftedgeinsider.com/en-us/download/?platform=linux and install browser in /opt")


def getResults (
    browser,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    context = browser.newContext()
    page = context.newPage()
    warmupIfSpecified(page, url + port, warmup)
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
    port: str,
    warmup: bool,
) -> json:
    runTcCommand(call)
    results = launchBrowser(pwInstance, browserType, url, h3, port, warmup=warmup)
    runTcCommand(reset)

    return results


def runTcCommand(
    command: str,
):
    if command:
        result = subprocess.run(command.split())
        if result.returncode > 0:
            print("Issue running TC!")
            print(result.args)
            print(result.stderr)
            print("--------------------------")


if __name__ == "__main__":

    main()
