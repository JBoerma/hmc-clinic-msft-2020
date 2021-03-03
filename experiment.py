"""QUIC Experiment Harness

Usage:
    experiment.py [--device DEVICE] [--conditions CONDITIONS ...] [--browsers BROWSERS ...] [--url URL] [--runs RUNS] [--out OUT] [--throughput THROUGHPUT] [--payloads PAYLOADS] [--ports PORTS ...] [options]
    
Arguments:
    --device DEVICE           Network device to modify [default: lo]
    --conditions CONDITIONS   List of network conditions [default: 4g-lte-good]
    --browsers BROWSERS       List of browsers to test [default: chromium edge]
    --throughput THROUGHPUT   Maximum number of request to send at a time [default: 1]
    --url URL                 URL to access [default: https://localhost]
    --runs RUNS               Number of runs in the experiment [default: 1]
    --out OUT                 File to output data to [default: results/results.db]
    --ports PORTS             List of ports to use (':443', ':444', ':445', ':446') [default: :443]
    --payloads PAYLOADS       List of sizes of the requsting payload [default: 100kb 1kb]

Options:
    -h --help                 Show this screen 
    --disable_caching         Disables caching
    --warmup                  Warms up connection
    --async                   Run experiment asynchronously
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
import psutil

# separating our own imports
import systemUtil
from launchBrowserAsync import launch_browser_async, get_results_async
from launchBrowserSync import launch_browser_sync, do_single_experiment_sync
from experiment_utils import apply_condition, reset_condition, setup_data_file_headers, write_big_table_data, write_timing_data


# generated command line code
CALL_FORMAT  = "sudo tc qdisc add dev {DEVICE} netem {OPTIONS}"
RESET_FORMAT = "sudo tc qdisc del dev {DEVICE}"


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
    # Process args
    args = docopt(__doc__, argv=None, help=True, version=None, options_first=False)
    device = args['--device']
    conditions = args['--conditions']
    browsers = args['--browsers']
    url = args['--url']
    runs = int(args['--runs'])
    out = args['--out']
    disable_caching = args['--disable_caching']
    warmup_connection = args['--warmup']
    throughput = int(args["--throughput"])
    ports = args['--ports']
    git_hash = subprocess.check_output(["git", "describe", "--always"]).strip()
    run_async = args['--async']
    payloads = args['--payloads'].split()
    # removes caching in nginx if necessary, starts up server
    # pre_experiment_setup(
    #    disable_caching=disable_caching,
    #    url            =url,
    # )
    
    # Setup data file headers  
    database = setup_data_file_headers(out=out)


    if not run_async:
        run_sync_experiment(
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
            database=        database,
            payloads =       payloads
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
        
    print("Finished!\n")


def run_sync_experiment(
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
    database, 
    payloads:        List[str],
):
    with sync_playwright() as p:
            for condition in tqdm(conditions, desc="Experiments"):
                experimentID = int(time.time()) # ensures no repeats
                # Start system monitoring
                util_process = subprocess.Popen(["python3", "systemUtil.py", str(experimentID)])
                tableData = (schemaVer, experimentID, url, serverVersion, git_hash, condition)
                write_big_table_data(tableData, database)
                whenRunH3 = [(h3, port, payload, browser) 
                                for browser in browsers 
                                for payload in payloads 
                                for port in server_ports * runs 
                                for h3 in [True, False]
                            ]
                random.shuffle(whenRunH3)
                # run the same experiment multiple times over h3/h2
                for (useH3, whichServer, payload, browser) in tqdm(whenRunH3):
                    # results = do_single_experiment_sync(condition, device, p, browser, useH3, url, whichServer.pop(), warmup=warmup)
                    results = do_single_experiment_sync(condition, device, p, browser, useH3, url, whichServer, payload, warmup=warmup) # TODO: replace with the line above once we have all servers loaded
                    results["experimentID"] = experimentID 
                    results["httpVersion"] = "h3" if useH3 else "h2" 
                    results["warmup"] = warmup
                    results["browser"] = browser 
                    results["payloadSize"] = payload 
                    results["netemParams"] = condition
                    # TODO: currently missing server, add server
                    write_timing_data(results, database)
                    httpVersion = "HTTP/3" if useH3 else "HTTP/2"
                    # Print info from latest run and then go back lines to prevent broken progress bars
                    tqdm.write(f"{browser}: {results['server']} ({httpVersion})")

                try:
                    util_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Cleaning up system monitoring subprocess
                    proc_pid = util_process.pid
                    process = psutil.Process(proc_pid)
                    for proc in process.children(recursive=True):
                        proc.kill()
                    process.kill()


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
