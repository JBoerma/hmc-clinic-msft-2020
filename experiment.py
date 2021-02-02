"""QUIC Experiment Harness

Usage:
    experiment.py experiment.py [--device DEVICE] [--options OPTIONS ...] [--browsers BROWSERS ...] [--url URL] [--runs RUNS] [--out OUT] [--throughput THROUGHPUT] [options] 
    
Arguments:
    --device DEVICE           Network device to modify [default: lo root]
    --options OPTIONS         tc-netem conditions to apply [default: delay 0ms]
    --browsers BROWSERS       List of browsers to test [default: firefox chromium edge]
    --throughput THROUGHPUT   Maximum number of request to send at a time [default: 1]
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
from launchBrowserAsync import launch_browser_async, get_results_async
from launchBrowserSync import launch_browser_sync, do_single_experiment_sync
from experiment_utils import run_tc_command, setup_data_file_headers, write_big_table_data, write_timing_data


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
    throughput = int(args["--throughput"])
    git_hash = subprocess.check_output(["git", "describe", "--always"]).strip()

    # removes caching in nginx if necessary, starts up server
    pre_experiment_setup(
        disable_caching=disable_caching,
        url            =url,
    )
    
    # Setup data file headers  
    database = setup_data_file_headers(out=out)


    # run_sync_experiment(
    #     schema_version=  "0",
    #     experiment_id=   str(int(time.time())),
    #     git_hash=        git_hash,
    #     server_version=  "0",
    #     device=          device,
    #     server_ports=    None, #[':443', ':444', ':445', ':7080/login.php'],
    #     options=         options,
    #     browsers=        browsers,
    #     url=             url,
    #     runs=            runs,
    #     disable_caching= disable_caching,
    #     warmup=          warmup_connection,
    #     database=        database,
    #     multi_server=    args['--multi-server'], # TODO - remove?  
    # )
    
    asyncio.get_event_loop().run_until_complete(runAsyncExperiment(
        schema_version=  "0",
        experiment_id=   str(int(time.time())),
        git_hash=        git_hash,
        server_version=  "0",
        device=          device,
        server_ports=    [':443', ':444', ':445', ':446'],
        options=         options,
        browsers=        browsers,
        url=             url,
        runs=            runs,
        disable_caching= disable_caching,
        warmup=          warmup_connection,
        throughput=      throughput,
        database=        database,
    ))

    post_experiment_cleanup(
        disable_caching=disable_caching,
    )
        
    print("Finished!\n")


def run_sync_experiment(
    schema_version:  str, 
    experiment_id:   str,
    git_hash:        str, 
    server_version:  str, 
    device:          str, 
    server_ports:    List[str],
    options:         List[str], 
    browsers:        List[str],
    url:             str,
    runs:            int, 
    disable_caching: bool,
    warmup:          bool,
    database, 
    multi_server:    bool,
):
    with sync_playwright() as p:
            for netemParams in tqdm(options, desc="Experiments"):
                reset = RESET_FORMAT.format(DEVICE=device)
                call  = CALL_FORMAT.format(DEVICE=device, OPTIONS=netemParams)

                experimentID = int(time.time()) # ensures no repeats
                tableData = (schemaVer, experimentID, url, serverVersion, git_hash, netemParams)
                write_big_table_data(tableData, database)
                for browser in tqdm(browsers, f"Browsers for '{netemParams}'"):
                    whenRunH3 = runs * [True] + runs * [False]
                    random.shuffle(whenRunH3)
                    perServer = runs // 4
                    # Ensure all servers are represented the same amount in H2 vs. H3
                    if runs < 4 or not multi_server:
                        whichServer = [':443'] * (runs * 2)
                    else:
                        servers1 = [':443', ':444', ':445', ':446'] * perServer
                        servers2 = [':443', ':444', ':445', ':446'] * perServer
                        random.shuffle(servers1)
                        random.shuffle(servers2)
                        whichServer = servers1 + servers2
                    # run the same experiment multiple times over h3/h2
                    for useH3 in tqdm(whenRunH3, desc=f"Runs for {browser}"):
                        results = do_single_experiment_sync(call, reset, p, browser, useH3, url, whichServer.pop(), warmup=warmup)
                        results["experimentID"] = experimentID
                        results["netemParams"] = netemParams
                        results["httpVersion"] = "h3" if useH3 else "h2"
                        results["warmup"] = warmup
                        results["browser"] = browser
                        write_timing_data(results, database)
                        httpVersion = "HTTP/3" if useH3 else "HTTP/2"
                        # Print info from latest run and then go back lines to prevent broken progress bars
                        tqdm.write(f"\033[F\033[K{browser}: {results['server']} ({httpVersion})       ")
                    print("", end="\033[F\033[K")
                print("", end="\033[F\033[K")


async def runAsyncExperiment(
    schema_version:  str, 
    experiment_id:   str,
    git_hash:        str, 
    server_version:  str, 
    device:          str, 
    server_ports:    List[str],
    options:         List[str], 
    browsers:        List[str],
    url:             str,
    runs:            int, 
    disable_caching: bool,
    warmup:          bool,
    throughput:      int,
    database,     
):     
    experiment_combos = [] 
    
    # TODO: fix this solution. Currently need a server_port to come up with
    # combinations, but surver_ports are incompatible with url that is 
    # passed in based on loigc below (url + port)
    if server_ports: 
        url="https://localhost"
    else:
        server_ports = [""]

    stuff = [(option, port, browser, version) for option in options for port in server_ports for browser in browsers for version in ["h2", "h3"]]
    for netem_params, server_port, browser, h_version in stuff: 
        experiment_combos.append(
            (netem_params, server_port, browser, h_version)
        )
        tableData = (
            schema_version, 
            experiment_id, 
            url, 
            server_version, 
            git_hash, 
            netem_params
        )
        write_big_table_data(tableData, database)

    # each combination of params gets equal weight
    experiment_runs = {combo: runs for combo in experiment_combos}

    async with async_playwright() as p: 
        outstanding = []
        while experiment_runs or outstanding:
            # choose a combo to work with
            for i in range(min(throughput, len(experiment_runs))):
                combo = random.choice(list(experiment_runs.keys()))
                if experiment_runs[combo] == 0: 
                    del experiment_runs[combo]
                    continue
                experiment_runs[combo] -= 1

                params, server_port, browser_name, h_version = combo 

                # set tc/netem params
                call = CALL_FORMAT.format(DEVICE=device, OPTIONS=params)
                run_tc_command(call)

                # TODO: move launchBrowser outside, experiments should share browser
                outstanding.append((
                    asyncio.create_task(
                        get_results_async(
                            p, browser_name, url, h_version=="h3", server_port, warmup
                        )
                    ), combo)
                )

            for item in outstanding:
                (task, combo) = item
                params, server_port, browser_name, h_version = combo 
                if task.done():
                    (results, browser) = task.result()
                    results["experimentID"] = experiment_id
                    results["netemParams"] = params
                    results["httpVersion"] = h_version
                    results["warmup"] = warmup
                    results["browser"] = browser_name
                    write_timing_data(results, database)
                    outstanding.remove(item)
                    asyncio.create_task(browser.close())
            await asyncio.sleep(1)
            # TODO: move browser close outside

    # only reset after all experiments
    reset = RESET_FORMAT.format(DEVICE=device)
    run_tc_command(reset)    


if __name__ == "__main__":
    main()
