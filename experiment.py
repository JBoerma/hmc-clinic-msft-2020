"""QUIC Experiment Harness

Usage:
    experiment.py experiment.py [--device DEVICE] [--options OPTIONS ...] [--browsers BROWSERS ...] [--url URL] [--runs RUNS] [--out OUT] [options] 
    
Arguments:
    --device DEVICE           Network device to modify [default: lo root]
    --options OPTIONS         tc-netem conditions to apply [default: delay 0ms]
    --browsers BROWSERS       List of browsers to test [default: firefox chromium edge]
    --url URL                 URL to access [default: https://localhost]
    --runs RUNS               Number of runs in the experiment [default: 1]
    --out OUT                 File to output data to [default: results/results.db]

Options:
    -h --help                 Show this screen 
    --disable_caching         Disables caching
    --multi-server            Uses all four server ports
    --warmup                  Warms up connection
"""

import os, cache_control, time, random, subprocess, csv, json, sqlite3, asyncio, itertools
from typing import List, Dict, Tuple
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from docopt import docopt
import random
from uuid import uuid4
from tqdm import tqdm
from sqlite3 import Connection

# separating our own imports
from launchBrowserAsync import launchBrowserAsync


# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"

experimentParameters = [
    "browser",
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
parameters = timingParameters + experimentParameters

big_table_fmt = {
    "schemaVer" : "TEXT",
    "experimentID" : "TEXT",
    "webPage" : "TEXT",
    "serverVersion" : "TEXT",
    "gitHash" : "TEXT",
    "netemParams" : "TEXT"
    }

cpu_usage_fmt = {
    "experimentID" : "TEXT",
    "cpuUsage" : "TEXT",
    "ioUsage" : "TEXT",
    "unixTime" : "INT"
}

timings_fmt = {
    "experimentID" : "TEXT",
    "browser" : "TEXT",
    "server" : "TEXT",
    "httpVersion" : "TEXT",
    "warmup" : "BOOL",
    "startTime" : "Float",
    "fetchStart" : "Float",
    "domainLookupStart" : "Float",
    "domainLookupEnd" : "Float",
    "connectStart" : "Float", 
    "secureConnectionStart" : "Float",
    "connectEnd" : "Float", 
    "requestStart" : "Float", 
    "responseStart" : "Float", 
    "responseEnd" : "Float",
    "domInteractive" : "Float",
    "domContentLoadedEventStart" : "Float", 
    "domContentLoadedEventEnd" : "Float", 
    "domComplete" : "Float", 
    "loadEventStart" : "Float",
    "loadEventEnd" : "Float",
}

schemaVer = "1.0"
serverVersion = "?"

# TODO: disable caching in all servers.
def pre_experiment_setup(
    disable_caching: bool, 
    url:             str, 
):
    if disable_caching:
        # Assumes that there is server caching by default
        cache_control.remove_server_caching("/usr/local/nginx/conf/nginx.conf", 23)
    # Make sure server is running
    if "localhost" in url or "127.0.0.1" in url:
        subprocess.run("sudo systemctl restart nginx.service".split())

def post_experiment_cleanup(
    disable_caching: bool, 
):
    if disable_caching:
        # Re-enable server caching
        cache_control.add_server_caching("/usr/local/nginx/conf/nginx.conf", 23, 9)


def main():   
    # Fix the program and server processes to specific cores
    def fix_process(process_name: str, cpu_core: str):
        processes = subprocess.check_output(['pgrep', '-f', process_name]).strip().decode('utf-8').replace("'","")
        for process in processes.split("\n"):
            subprocess.check_output(['sudo','taskset', '-p', cpu_core, process]).strip().decode('utf-8').replace("'","")
    fix_process("experiment.py", "01")
    try: # try/except to deal with 
        fix_process("nginx", "02")
    except subprocess.CalledProcessError as e:
        print(f"Nginx server processes not found. Failed command: {e}")

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
    out = args['--out']
    disable_caching = args['--disable_caching']
    warmup_connection = args['--warmup']
    git_hash = subprocess.check_output(["git", "describe", "--always"]).strip()

    # removes caching in nginx if necessary, starts up server
    pre_experiment_setup(
        disable_caching=disable_caching,
        url            =url,
    )
    
    # Setup data file headers  
    if not os.path.exists(out):
        big_table = ""
        for key in big_table_fmt.keys():
            big_table += f"{key} {big_table_fmt[key]}, "
        cpu_time = ""
        for key in cpu_usage_fmt.keys():
            cpu_time += f"{key} {cpu_usage_fmt[key]}, "
        timings = ""
        for key in timings_fmt.keys():
            timings += f"{key} {timings_fmt[key]}, "
        create_big_db = f"CREATE TABLE big_table ({big_table[:-2]});"
        create_cpu_db = f"CREATE TABLE cpu_time ({cpu_time[:-2]});"
        create_timing_db = f"CREATE TABLE timings ({timings[:-2]})"
        database = sqlite3.connect(out)  
        database.execute(create_big_db)
        database.execute(create_cpu_db)
        database.execute(create_timing_db)
        database.commit()
    else:
        database = sqlite3.connect(out)  

    with sync_playwright() as p:
        schema_servers = set()
        for netemParams in tqdm(options, desc="Experiments"):
            reset = RESET_FORMAT.format(DEVICE=device)
            call  = CALL_FORMAT.format(DEVICE=device, OPTIONS=netemParams)

            experimentID = int(time.time()) # ensures no repeats
            tableData = (schemaVer, experimentID, url, serverVersion, git_hash, netemParams)
            writeBigTableData(tableData, database)
            for browser in tqdm(browsers, f"Browsers for '{netemParams}'"):
                whenRunH3 = runs * [True] + runs * [False]
                random.shuffle(whenRunH3)
                perServer = runs // 4
                # Ensure all servers are represented the same amount in H2 vs. H3
                if runs < 4 or not args['--multi-server']:
                    whichServer = [':443'] * (runs * 2)
                else:
                    servers1 = [':443', ':444', ':445', ':7080/login.php'] * perServer
                    servers2 = [':443', ':444', ':445', ':7080/login.php'] * perServer
                    random.shuffle(servers1)
                    random.shuffle(servers2)
                    whichServer = servers1 + servers2
                # run the same experiment multiple times over h3/h2
                for useH3 in tqdm(whenRunH3, desc=f"Runs for {browser}"):
                    results = runExperiment(call, reset, p, browser, useH3, url, whichServer.pop(), warmup=warmup_connection)
                    results["experimentID"] = experimentID
                    results["netemParams"] = netemParams
                    results["browser"] = browser
                    results["httpVersion"] = "h3" if useH3 else "h2"
                    results["warmup"] = warmup_connection
                    results["browser"] = browser
                    writeTimingData(results, database)
                    httpVersion = "HTTP/3" if useH3 else "HTTP/2"
                    schema_servers.add(results['server']) # Collect servers for big table
                    # Print info from latest run and then go back lines to prevent broken progress bars
                    tqdm.write(f"\033[F\033[K{browser}: {results['server']} ({httpVersion})       ")
                print("", end="\033[F\033[K")
            print("", end="\033[F\033[K")
    
    # asyncio.get_event_loop().run_until_complete(runAsyncExperiment(
    #     schema_version=  "0",
    #     experiment_id=   str(int(time.time())),
    #     git_hash=        "0",
    #     server_version=  "0",
    #     device=          device,
    #     servers=         [':443', ':444', ':445', ':7080/login.php'],
    #     options=         options,
    #     browsers=        browsers,
    #     url=             url,
    #     runs=            runs,
    #     disable_caching= disable_caching,
    #     warmup=          warmup_connection,
    # ))

    post_experiment_cleanup(
        disable_caching=disable_caching,
    )
        
    print("Finished!\n")

async def warmupIfSpecifiedAsync(
    playwrightPage: "Page",
    url: str,
    warmup: bool,
): 
    if warmup:
        cache_buster = url + "?send_data_again"
        await playwrightPage.goto(cache_buster)

async def getResultsAsync(
    browser,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    context = await browser.new_context()
    page = await context.new_page()

    cache_buster = f"?{time.time()}"
    await warmupIfSpecifiedAsync(page, url + port, warmup)
    response = await page.goto(url + port + cache_buster)

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    timingResponse = await page.evaluate(timingFunction)

    performanceTiming = json.loads(timingResponse)
    performanceTiming['server'] = response.headers['server']
    
    # close context, allowing next call to use same browser
    await context.close()

    return performanceTiming

async def runAsyncExperiment(
    schema_version:  str, 
    experiment_id:   str,
    git_hash:        str, 
    server_version:  str, 
    device:          str, 
    servers:         List[str],
    options:         List[str], 
    browsers:        List[str],
    url:             str,
    runs:            int, 
    disable_caching: bool,
    warmup:          bool,
):     
    experiment_combos = \
        [
            (netem_params, server, browser, h_version) 
            for netem_params in options
            for server in servers
            for browser in browsers 
            for h_version in ["h2", "h3"]
        ]

    # each combination of params gets equal weight
    experiment_runs   = {combo: runs for combo in experiment_combos}
    
    async with async_playwright() as p: 
        while experiment_runs:
            # choose a combo to work with
            combo = random.choice(list(experiment_runs.keys()))
            if experiment_runs[combo] == 0: 
                del experiment_runs[combo]
                continue
            experiment_runs[combo] -= 1

            params, server, browser_name, h_version = combo 

            # #####################################################
            # TODO: replace logic after schema is merged
            name = browser_name + "_" + params.replace(" ", "_")
            directoryPath = "results"
            csvFileName = f"{directoryPath}/{name}.csv"
            # Setup data file headers
            os.makedirs(os.path.dirname(csvFileName), exist_ok=True)
            if not os.path.exists(csvFileName):
                with open(csvFileName, 'w', newline='\n') as outFile:
                    csvWriter = csv.writer(outFile)
                    csvWriter.writerow(parameters)
            # #####################################################

            # set tc/netem params
            call = CALL_FORMAT.format(DEVICE=device, OPTIONS=params)
            runTcCommand(call)

            # TODO: move launchBrowser outside, experiments should share browser
            browser = await launchBrowserAsync(
                p, browser_name, url, h_version=="h3", server 
            )
            performance_timing = await getResultsAsync(
                browser, url, h_version=="h3", server, warmup
            )

            # #####################################################
            # TODO: replace logic after schema is merged
            performance_timing["experimentID"] = experiment_id
            performance_timing["netemParams"] = params
            performance_timing["httpVersion"] = h_version
            performance_timing["warmup"] = warmup
            writeData(performance_timing, csvFileName)
            # #####################################################

            # TODO: move browser close outside
            await browser.close()

    
    # only reset after all experiments
    reset = RESET_FORMAT.format(DEVICE=device)
    runTcCommand(reset)    
    
def writeData(data: json, csvFileName: str):
    with open(csvFileName, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=parameters, extrasaction='ignore')
        csvWriter.writerow(data)

def writeBigTableData(data: json, db: Connection):
    insert = f"INSERT INTO big_table VALUES ({ ('?,' * len(big_table_fmt))[:-1]})"
    db.execute(insert, data)
    db.commit()


def writeTimingData(data: json, db: Connection):
    insert = f"INSERT INTO timings VALUES ({ ('?,' * len(timings_fmt))[:-1]})"
    dataTuple = tuple([data[key] for key in timings_fmt.keys()])
    db.execute(insert, dataTuple)
    db.commit()

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

    browser = pwInstance.firefox.launch(
        headless=True,
        firefox_user_prefs=firefoxPrefs,
    )
    return getResults(browser, url, h3, port, warmup)

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
    except:
        browser =  pwInstance.chromium.launch(
            headless=True,
            args=chromiumArgs,
        )
    return getResults(browser, url, h3, port, warmup)

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
    except:
        browser = pwInstance.chromium.launch(
            headless=True,
            executablePath='/opt/microsoft/msedge-dev/msedge',
            args=edgeArgs,
        )
    return getResults(browser, url, h3, port, warmup)
    

def getResults (
    browser,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    context = browser.new_context()
    page = context.new_page()
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
