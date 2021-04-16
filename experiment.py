"""QUIC Experiment Harness

Usage:
    experiment.py [--device DEVICE] [--conditions CONDITIONS ...] [--browsers BROWSERS ...] [--urls URLS ...] [--runs RUNS] [--out OUT] [--throughput THROUGHPUT] [--payloads PAYLOADS ...] [--ports PORTS ...] [--endpoints ENDPOINTS ...] [options]
    
Arguments:
    --device DEVICE           Network device to modify [default: lo]
    --conditions CONDITIONS   List of network conditions [default: 4g-lte-good]
    --browsers BROWSERS       List of browsers to test [default: chromium edge firefox]
    --throughput THROUGHPUT   Maximum number of request to send at a time when --async is set [default: 1]
    --urls URLS               URL to access
    --runs RUNS               Number of runs in the experiment [default: 1]
    --out OUT                 File to output data to [default: results/results.db]
    --ports PORTS             List of ports to use (':443', ':444', ':445', ':446') [default: :443]
    --json JSON               JSON file of arguments
    --payloads PAYLOADS       List of sizes of the requesting payload (1kb, 10kb, 100kb) [default: 1kb 10kb 100kb]
    --endpoints ENDPOINTS     Endpoint to hit. (server-nginx server-nginx-quiche server-caddy server-openlitespeed facebook google cloudflare)

Options:
    -h --help                 Show this screen 
    --disable_caching         Disables caching
    --warmup                  Warms up connection
    --async                   Run experiment asynchronously
    --qlog                    Turns on QLog logging
    --pcap                    Turns on packet capturing using TShark
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
# file handler logs DEBUG, INFO, and above to file
log_time = time.time_ns()
log_file = f"{log_time}.log"
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
pcap_process = None

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
        global util_process, pcap_process
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
        if pcap_process:
            try:
                pcap_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Cleaning up system monitoring subprocess
                proc_pid = pcap_process.pid
                process = psutil.Process(proc_pid)
                for proc in process.children(recursive=True):
                    proc.kill()
                process.kill()
        sys.exit()


def main():   
    logger.info(f"Logs at {log_file}")

    # Process args
    args = docopt(__doc__, argv=None, help=True, version=None, options_first=False)
    # If JSON, merge arguments in - will overwrite overlapping arguments
    if args['--json']:
        json_args = json.loads(args['--json'])
        args.update(json_args)
    logger.info(args)

    device = args['--device']
    killer = ResetTCOnExit(device)
    conditions = args['--conditions']
    browsers = args['--browsers']

    runs = int(args['--runs'])
    out = args['--out']
    disable_caching = args['--disable_caching']
    warmup_connection = args['--warmup']
    throughput = int(args["--throughput"])
    ports = args['--ports']
    git_hash = subprocess.check_output(["git", "describe", "--always"]).strip()
    run_async = args['--async']
    qlog = args['--qlog']
    pcap = args['--pcap']
    # removes caching in nginx if necessary, starts up server
    # pre_experiment_setup(
    #    disable_caching=disable_caching,
    #    url            =url,
    # )
    # Handle urls, endpoints, payloads
    urls = args['--urls']
    payloads = args['--payloads']
    endpoints = args['--endpoints']

    # save args to JSON file
    with open(f"{log_time}_args.json", "w") as outfile: 
        json.dump(args, outfile)

    endpts: List[Endpoint] = []
    # Each url gets its own endpoint. Exceptions are handled silently - 
    # the script will try to continue with whatever works
    for url in urls:
        protocols = ["http://", "https://"]
        if all(protocol != url[0:len(protocol)] for protocol in protocols):
            logger.warning(f"There is no protocol (e.g. one of {protocols} in the url: {url}")

        try: 
            endpts.append(Endpoint(url, None, None))
        except Exception: 
            logger.exception(f"Error in creating endpoint for url: {url}")
    # Each payload/endpoint combination also gets its own
    for (endpoint, payload) in itertools.product(endpoints, payloads):
        try: 
            endpts.append(Endpoint(None, endpoint, payload))
        except Exception: 
            logger.exception(f"Error in creating endpoint for endpoint - payload: {endpoint} - {payload}")
    
    if len(endpts) == 0: 
        logger.error("There are no valid endpoints or urls. Aborting...")
        sys.exit()
    
    # Setup data file headers  
    database = setup_data_file_headers(out=out)

    if not run_async:
        run_sync_experiment(
            schema_version=  "0",
            git_hash=        git_hash,
            server_version=  "0",
            device=          device,
            endpoints=       endpts,
            conditions=      conditions,
            browsers=        browsers,
            runs=            runs,
            out=             out,
            disable_caching= disable_caching,
            warmup=          warmup_connection,
            database=        database,
            qlog=            qlog,
            pcap=            pcap,
        )
    else: # TODO this is broken
        asyncio.get_event_loop().run_until_complete(run_async_experiment(
            schema_version=  "0",
            experiment_id=   str(int(time.time())),
            git_hash=        git_hash,
            server_version=  "0",
            device=          device,
            server_ports=    ports,
            conditions=      conditions,
            browsers=        browsers,
            url=             urls,
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
    endpoints:       List[Endpoint],
    conditions:      List[str], 
    browsers:        List[str],
    runs:            int, 
    out:             str,
    disable_caching: bool,
    warmup:          bool,
    qlog:            bool,
    pcap:            bool,
    database, 
):
    with sync_playwright() as p:
        # TODO randomize endpoint and condition. There is no reason to not randomize them.
        for endpoint in tqdm(endpoints, desc="Endpoints"): 
            logger.info(f"URL: {endpoint.get_url()}")
            url = endpoint.get_url()
            for condition in tqdm(conditions, desc="Experiments"):
                logger.info(f"Condition: {condition}")
                experiment_id = int(time.time()) # ensures no repeats
                logger.debug(f"Experiment ID: {experiment_id}")
                for browser in browsers:
                    qlog_dir = f"{os.getcwd()}/results/qlogs/{browser}/{experiment_id}"
                    os.makedirs(qlog_dir, exist_ok = True)
                    pcap_dir = f"{os.getcwd()}/results/packets/{browser}/{experiment_id}"
                    os.makedirs(pcap_dir, exist_ok = True)

                # Start system monitoring
                global util_process
                util_process = subprocess.Popen(["python3", "systemUtil.py", str(experiment_id), 'client', str(out)])
                tableData = (schema_version, experiment_id, url, server_version, git_hash, condition)
                write_big_table_data(tableData, database)

                # Start server monitoring if accessing our own server
                ssh_client = None
                if endpoint.is_on_server():
                    ssh_client = start_server_monitoring(experiment_id, str(out))

                params = [(h3, browser) 
                    for browser in browsers 
                    for h3 in [True, False]
                ] * runs
                random.shuffle(params)

                # run the same experiment multiple times over h3/h2
                for (useH3, browser) in tqdm(params, desc="Individual Runs"):
                    run_id = int(time.time())
                    if pcap:
                        global pcap_process
                        pcap_file = f"results/packets/{browser}/{experiment_id}/{run_id}-{useH3}"
                        pcap_process = subprocess.Popen(f"tshark -i {device} -Q -w {os.getcwd()}/{pcap_file}.pcap".split())

                    results = do_single_experiment_sync(condition, device, p, browser, useH3, 
                                                            endpoint, warmup, qlog, pcap,
                                                            experiment_id, run_id)
                    results["experimentID"] = experiment_id
                    results["httpVersion"] = "h3" if useH3 else "h2" 
                    results["warmup"] = warmup
                    results["browser"] = browser 
                    results["payloadSize"] = endpoint.get_payload() 
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
                    if pcap:
                        try:
                            pcap_process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            # Cleaning up system monitoring subprocess
                            proc_pid = pcap_process.pid
                            process = psutil.Process(proc_pid)
                            for proc in process.children(recursive=True):
                                proc.kill()
                            process.kill()
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
    if not server_ports: 
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

    # set up progress bar
    pbar = tqdm(total = runs * len(experiment_combos), desc="Experiments")
    async with async_playwright() as p: 
        outstanding = []
        while experiment_runs:
            # choose a combo to work with
            combo = random.choice(list(experiment_runs.keys()))
            if experiment_runs[combo] <= 0: 
                del experiment_runs[combo]
                continue
            experiment_runs[combo] -= 1
            pbar.update(1)
            condition, server_port, browser_name, h_version, payload = combo 

            # set tc/netem params
            apply_condition(device, condition)

            # one run is a run of "througput" page visits TODO revist this after meeting
            for _ in range(throughput):
                # move launchBrowser outside, experiments should share browser
                browser = await launch_browser_async(
                    p, browser_name, url, h_version == "h3", server_port
                )

                outstanding.append((
                    asyncio.create_task(
                        get_results_async(
                            browser, url, h_version=="h3", server_port, payload, warmup
                        )
                    ), combo)
                )
            await clean_outstanding(
                outstanding=outstanding, 
                warmup=warmup, 
                database=database, 
                experiment_id=experiment_id,
                device=device
            ) 
            # TODO: move browser close outside
        
        while outstanding:
            await clean_outstanding(
                outstanding=outstanding, 
                warmup=warmup, 
                database=database, 
                experiment_id=experiment_id,
                device=device
            ) 

    # only reset after all experiments
    # reset_condition(device)
    pbar.close()


async def clean_outstanding(outstanding: List, warmup: bool, database, experiment_id: str, device: str): 
    for item in outstanding:
        (task, combo) = item
        # TODO - server_port is unused. Is this bc we don't have a column for it?
        condition, server_port, browser_name, h_version, payload = combo
        if task.done():
            results, browser = task.result()
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
    reset_condition(device)


if __name__ == "__main__":
    main()
