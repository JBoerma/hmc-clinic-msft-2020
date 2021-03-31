"""QUIC Experiment Harness

Usage:
    experiment.py [--device DEVICE] [--conditions CONDITIONS ...] [--browsers BROWSERS ...] [--urls URLS ...] [--runs RUNS] [--out OUT] [--throughput THROUGHPUT] [--payloads PAYLOADS] [--ports PORTS ...] [--endpoints ENDPOINTS ...] [options]
    
Arguments:
    --device DEVICE           Network device to modify [default: lo]
    --conditions CONDITIONS   List of network conditions [default: 4g-lte-good]
    --browsers BROWSERS       List of browsers to test [default: chromium edge]
    --throughput THROUGHPUT   Maximum number of request to send at a time [default: 1]
    --urls URLS               URL to access
    --runs RUNS               Number of runs in the experiment [default: 100]
    --out OUT                 File to output data to [default: results/results.db]
    --ports PORTS             List of ports to use (':443', ':444', ':445', ':446') [default: :443]
    --payloads PAYLOADS       List of sizes of the requsting payload (1kb, 10kb, 100kb) [default: 1kb 10kb 100kb]
    --endpoints ENDPOINTS     Endpoint to hit. (server-nginx server-nginx-quiche server-caddy server-openlitespeed facebook google cloudflare)

Options:
    -h --help                 Show this screen 
    --disable_caching         Disables caching
    --warmup                  Warms up connection
    --async                   Run experiment asynchronously
    --qlog                    Turns on QLog logging
"""

import sys, os, time, random, subprocess, json, sqlite3, asyncio, itertools
import cache_control
from subprocess import Popen
from typing import List, Dict, Tuple
import cache_control
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from docopt import docopt
from tqdm import tqdm
from sqlite3 import Connection
import psutil
import signal

# separating our own imports
from launchBrowserAsync import launch_browser_async, get_results_async
from launchBrowserSync import launch_browser_sync, do_single_experiment_sync
from experiment_utils import apply_condition, reset_condition, setup_data_file_headers, write_big_table_data, write_timing_data
from ssh_utils import start_server_monitoring, end_server_monitoring, on_server, get_server_private_ip
from endpoint import Endpoint

# Thanks to https://stackoverflow.com/questions/38543506/change-logging-print-function-to-tqdm-write-so-logging-doesnt-interfere-wit
import logging
class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)  


# set up logging, log file...
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')

# console handler logs WARNING, ERROR, and CRITICAL to console
consoleHandler = TqdmLoggingHandler()
consoleHandler.setLevel(logging.INFO)
consoleHandler.setFormatter(formatter)
# file hanlder logs DEBUG, INFO, and above to file
log_file = f"{time.time()}.log"
fileHandler = logging.FileHandler(log_file)
fileHandler.setLevel(logging.DEBUG)
fileHandler.setFormatter(formatter)
# add handlers to logger
logger.addHandler(consoleHandler)
logger.addHandler(fileHandler)


# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"
util_process = None

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


# Reset TC Params on exit
class ResetTCOnExit:
    def __init__(self, dev: str):
        self.dev = dev
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        reset_condition(self.dev)
        # TODO after logging PR is in, replace with log
        print(f"Exiting Program due to SIGNUM {signum}", flush=True)
        global util_process
        if util_process:
            try:
                util_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Cleaning up system monitoring subprocess
                proc_pid = util_process.pid
                process = psutil.Process(proc_pid)
                for proc in process.children(recursive=True):
                    proc.kill()
                process.kill()
        sys.exit()

def handle_endpoint(url, ports, endpoint, payloads):
     # Set up public endpoints. TODO FIX THIS. THIS IS MINIMUM WORKING EX.
    with open("external.json") as external_json:
        endpoint_urls = json.load(external_json)
        if not url:
            if not endpoint:
                logger.error("Need to specify a url or an endpoint. url has precedence.")
                sys.exit()

            try:
                url = endpoint_urls[endpoint][payloads[0]]
            except KeyError: 
                logger.exception(f"The endpoint:payload combination {endpoint}:{payloads[0]} does not exist")
                sys.exit()

            if endpoint != "server":
                ports = [""] # HACK - need to fix
    return url, ports

def main():   
    # Process args
    args = docopt(__doc__, argv=None, help=True, version=None, options_first=False)
    logger.info(args)

    device = args['--device']
    killer = ResetTCOnExit(device)

    conditions = args['--conditions']
    browsers = args['--browsers']
    urls = args['--urls']
    url = None
    if urls: 
        url = urls[0]

    runs = int(args['--runs'])
    out = args['--out']
    disable_caching = args['--disable_caching']
    warmup_connection = args['--warmup']
    throughput = int(args["--throughput"])
    ports = args['--ports']
    git_hash = subprocess.check_output(["git", "describe", "--always"]).strip()
    run_async = args['--async']
    payloads = args['--payloads'].split()
    qlog = args['--qlog']
    # removes caching in nginx if necessary, starts up server
    # pre_experiment_setup(
    #    disable_caching=disable_caching,
    #    url            =url,
    # )

    # ENDPOINT takes precedence over url
    endpt: str = "" 
    if not url: 
        endpt = args['--endpoints'][0]
    # url, ports = handle_endpoint(url, ports, endpoint, payloads)
    # TODO - pass list of endpoints down into run_sync_experiment
    endpoint = Endpoint(url, endpt, payloads[0])
    
    # Setup data file headers  
    database = setup_data_file_headers(out=out)

    logger.warning("Be aware that only the first of urls, ports, and runs is used.")
    if not run_async:
        run_sync_experiment(
            schema_version=  "0",
            git_hash=        git_hash,
            server_version=  "0",
            device=          device,
            server_ports=    [endpoint.get_port()],
            conditions=      conditions,
            browsers=        browsers,
            url=             endpoint.get_url(),
            runs=            runs,
            out=             out,
            disable_caching= disable_caching,
            warmup=          warmup_connection,
            database=        database,
            payloads=        [endpoint.get_payload()],
            qlog=            qlog,
        )
    else:
        asyncio.get_event_loop().run_until_complete(run_async_experiment(
            schema_version=  "0",
            experiment_id=   str(int(time.time())),
            git_hash=        git_hash,
            server_version=  "0",
            device=          device,
            server_ports=    ports,
            conditions=      conditions,
            browsers=        browsers,
            url=             url,
            runs=            runs,
            disable_caching= disable_caching,
            warmup=          warmup_connection,
            throughput=      throughput,
            database=        database,
            payloads =       payloads

        ))

    # post_experiment_cleanup(
    #     disable_caching=disable_caching,
    # )
        
    logger.info(f"Finished! View logs at {log_file}")


def run_sync_experiment(
    schema_version:  str,
    git_hash:        str, 
    server_version:  str, 
    device:          str, 
    server_ports:    List[str],
    conditions:      List[str], 
    browsers:        List[str],
    url:             str,
    runs:            int, 
    out:             str,
    disable_caching: bool,
    warmup:          bool,
    qlog:            bool,
    database, 
    payloads:        List[str],
):
    with sync_playwright() as p:
            for condition in tqdm(conditions, desc="Experiments"):
                experiment_id = int(time.time()) # ensures no repeats
                logger.debug(f"Experiment ID: {experiment_id}")

                # Start system monitoring
                global util_process
                util_process = subprocess.Popen(["python3", "systemUtil.py", str(experiment_id), 'client', str(out)])
                tableData = (schema_version, experiment_id, url, server_version, git_hash, condition)
                write_big_table_data(tableData, database)

                # Start server monitoring if accessing our own server
                ssh_client = None
                if on_server(url=url):
                    ssh_client = start_server_monitoring(experiment_id, str(out))

                whenRunH3 = [(h3, port, payload, browser) 
                                for browser in browsers 
                                for payload in payloads 
                                for port in server_ports * runs 
                                for h3 in [True, False]
                            ]
                random.shuffle(whenRunH3)
                # run the same experiment multiple times over h3/h2
                for (useH3, whichServer, payload, browser) in tqdm(whenRunH3):
                    results = do_single_experiment_sync(condition, device, p, browser, useH3, url, whichServer, payload, warmup, qlog, experiment_id)
                    results["experimentID"] = experiment_id
                    results["httpVersion"] = "h3" if useH3 else "h2" 
                    results["warmup"] = warmup
                    results["browser"] = browser 
                    results["payloadSize"] = payload 
                    results["netemParams"] = condition
                    # TODO: currently missing server, add server
                    write_timing_data(results, database)
                    httpVersion = "HTTP/3" if useH3 else "HTTP/2"
                    # Print info from latest run and then go back lines to prevent broken progress bars
                    # if the request fails, we will print out the message in the console
                    if 'server' in results.keys():
                        logger.debug(f"{browser}: {results['server']} ({httpVersion})")
                    else:
                        logger.error(f"{browser}: {'error'}({httpVersion})")
                try:
                    util_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Cleaning up system monitoring subprocess
                    proc_pid = util_process.pid
                    process = psutil.Process(proc_pid)
                    for proc in process.children(recursive=True):
                        proc.kill()
                    process.kill()
                
                # end server monitoring 
                if on_server(url=url):
                    end_server_monitoring(ssh=ssh_client)


async def run_async_experiment(
    schema_version:  str, 
    experiment_id:   str,
    git_hash:        str, 
    server_version:  str, 
    device:          str, 
    server_ports:    List[str],
    conditions:      List[str], 
    browsers:        List[str],
    url:             str,
    runs:            int, 
    disable_caching: bool,
    warmup:          bool,
    throughput:      int,
    database,     
    payloads:        List[str],
):     
    experiment_combos = [] 
    
    # TODO: fix this solution. Currently need a server_port to come up with
    # combinations, but surver_ports are incompatible with url that is 
    # passed in based on loigc below (url + port)
    if server_ports: 
        url="https://localhost"
    else:
        server_ports = [""]

    stuff = [(condition, port, browser, version, payload) 
        for condition in conditions 
        for port in server_ports 
        for browser in browsers 
        for version in ["h2", "h3"]
        for payload in payloads
    ]

    for condition, server_port, browser, h_version, payload in stuff: 
        experiment_combos.append(
            (condition, server_port, browser, h_version, payload)
        )
        tableData = (
            schema_version, 
            experiment_id, 
            url, 
            server_version, 
            git_hash, 
            condition
        )
        write_big_table_data(tableData, database)

    # each combination of params gets equal weight
    experiment_runs = {combo: runs for combo in experiment_combos}

    async with async_playwright() as p: 
        outstanding = []
        while experiment_runs:
            # choose a combo to work with
            combo = random.choice(list(experiment_runs.keys()))
            if experiment_runs[combo] <= 0: 
                del experiment_runs[combo]
                continue
            experiment_runs[combo] -= 1

            condition, server_port, browser_name, h_version, payload = combo 

            # set tc/netem params
            apply_condition(device, condition)

            # one run is a run of "througput" page visits TODO revist this after meeting
            for _ in range(throughput):
                # TODO: move launchBrowser outside, experiments should share browser
                outstanding.append((
                    asyncio.create_task(
                        get_results_async(
                            p, browser_name, url, h_version=="h3", server_port, payload, warmup
                        )
                    ), combo)
                )

            await clean_outstanding(
                outstanding=outstanding, 
                warmup=warmup, 
                database=database, 
                experiment_id=experiment_id
            ) 
            # TODO: move browser close outside
        
        while outstanding:
            await clean_outstanding(
                outstanding=outstanding, 
                warmup=warmup, 
                database=database, 
                experiment_id=experiment_id
            ) 

    # only reset after all experiments
    reset_condition(device)


async def clean_outstanding(outstanding: List, warmup: bool, database, experiment_id: str): 
    for item in outstanding:
        (task, combo) = item
        # TODO - server_port is unused. Is this bc we don't have a column for it?
        condition, server_port, browser_name, h_version, payload = combo
        if task.done():
            (results, browser) = task.result()
            results["experimentID"] = experiment_id
            results["netemParams"] = condition
            results["httpVersion"] = h_version
            results["warmup"] = warmup
            results["browser"] = browser_name
            results["payloadSize"] = payload
            write_timing_data(results, database)
            outstanding.remove(item)
            asyncio.create_task(browser.close())
    await asyncio.sleep(1)


if __name__ == "__main__":
    main()
