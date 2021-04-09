import json
import sys
from typing import List
from tqdm import tqdm
import re, os, time, glob

from experiment_utils import reset_condition, apply_condition
from endpoint import Endpoint

import logging
logger = logging.getLogger('__main__.' + __name__)

"""
A single sync experiment consists of a single request.
First emulate the desired network condition,
then launch the desired broswer, go to the desired page,
and get the timing result (or error),
last, remove the TC setting.
Return the navigation timing data
"""
def do_single_experiment_sync(
    condition: str, 
    device: str, 
    pw_instance: "SyncPlaywrightContextManager", 
    browser_type: str, 
    h3: bool,
    endpoint: Endpoint,
    warmup: bool,
    qlog: bool,
    pcap: bool,
    expnt_id: int,
    run_id: int,
) -> json:
    apply_condition(device, condition)
    results = launch_browser_sync(pw_instance, browser_type, h3, endpoint, warmup, qlog, pcap, expnt_id, run_id)
    reset_condition(device)

    return results

"""
Invoke the specified browser launch functions, return the navigation timing data
"""
def launch_browser_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    browser_type: str,
    h3: bool,
    endpoint: Endpoint,
    warmup: bool,
    qlog: bool,
    pcap: bool,
    expnt_id: int,
    run_id: int,
) -> json:
    browser = None
    if browser_type  ==  "firefox":
        browser = launch_firefox_sync(pw_instance, h3, endpoint, warmup, qlog, pcap, expnt_id, run_id)
    elif browser_type  ==  "chromium":
        browser = launch_chromium_sync(pw_instance, h3, endpoint, warmup, qlog, pcap, expnt_id, run_id)
    elif browser_type  ==  "edge":
        browser = launch_edge_sync(pw_instance, h3, endpoint, warmup, qlog, pcap, expnt_id, run_id)
    # if browser fails to launch, stop this request and write to the database
    if not browser: 
        return {"error": "launch_browser_failed"}

    result = get_results_sync(browser, h3, endpoint, warmup)
    if h3 and qlog and browser_type == "firefox":
        # change qlogś name so that it will be saved to results/qlogs/firefox/[experimentID]
        for qlog in glob.glob("/tmp/qlog_*/*.qlog", recursive=True):
            qlog_dir = f"{os.getcwd()}/results/qlogs/sync-{expnt_id}/firefox"
            os.rename(qlog, f"{qlog_dir}/{run_id}.qlog")
    return result
"""
Launch the firefox browser
"""
def launch_firefox_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    h3: bool,
    endpoint: Endpoint,
    warmup: bool,
    qlog: bool,
    pcap: bool,
    expnt_id: int,
    run_id: int,
) -> json:
    # set up firefox preference
    firefox_prefs = {}
    firefox_prefs["privacy.reduceTimerPrecision"] = False
    if h3:
        if qlog:
            firefox_prefs["network.http.http3.enable_qlog"] = True  # enable qlog
        firefox_prefs["network.http.http3.enabled"] = True # enable h3 protocol
        # the openlightspeed server works with a different h3 version than the rest of the servers

        port = endpoint.get_port()
        h3_version = "29"
        if endpoint.get_endpoint() == "server-openlitespeed":
            h3_version = "27"
        firefox_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{endpoint.port};h3-{h3_version}=:{port}"       
    # attempt to launch browser
    try:
        if pcap:
            pcap_file = f"{os.getcwd()}/results/packets/sync-{expnt_id}/firefox/{run_id}-{h3}.keys"
            return pw_instance.firefox.launch(
                headless=True,
                firefox_user_prefs=firefox_prefs,
                env={"SSLKEYLOGFILE": pcap_file}
            )
        else:
            return pw_instance.firefox.launch(
                headless=True,
                firefox_user_prefs=firefox_prefs,
            )
    except Exception as e:  # if browser fails to launch, stop this request and write to the database
        logger.exception(str(e))
        return None

"""
Launch the chromium browser
"""
def launch_chromium_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    h3: bool,
    endpoint: Endpoint,
    warmup: bool,
    qlog: bool,
    pcap: bool,
    expnt_id: int,
    run_id: int,
) -> json:
    chromium_args = []
    if h3:
        # set up chromium arguments for enabling h3, qlog, h3 version
        chromium_args = ["--enable-quic", "--quic-version=h3-29"]
        if endpoint.is_on_server(): 
            domain = endpoint.get_domain()
            port = endpoint.get_port()
            chromium_args.append(f"--origin-to-force-quic-on={domain}:{port}")
        else: 
            pass # TODO - do we need to force quic on other endpoints?
        
        if qlog:
            # set up a directory results/qlogs/chromium/[experimentID] to save qlog
            qlog_dir = f"{os.getcwd()}/results/qlogs/sync-{expnt_id}/chromium/"
            chromium_args.append(f"--log-net-log={qlog_dir}/{run_id}.json")
    # attempt to launch browser
    try:
        if pcap:
            pcap_file = f"{os.getcwd()}/results/packets/sync-{expnt_id}/chromium/{run_id}-{h3}.keys"
            return pw_instance.chromium.launch(
                headless=True,
                args=chromium_args,
                env={"SSLKEYLOGFILE": pcap_file}
            )
        else:
            return pw_instance.chromium.launch(
                headless=True,
                args=chromium_args,
            )
    except Exception as e:  # if browser fails to launch, stop this request and write to the database
        logger.error(str(e))
        return None

"""
Launch the edge browser
"""
def launch_edge_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    h3: bool,
    endpoint: Endpoint,
    warmup: bool,
    qlog: bool,
    pcap: bool,
    expnt_id: int,
    run_id: int,
) -> json:
    edge_args = []
    if (h3) :
        chromium_args = ["--enable-quic", "--quic-version=h3-29"]
        if endpoint.is_on_server(): 
            domain = endpoint.get_domain()
            port = endpoint.get_port()
            chromium_args.append(f"--origin-to-force-quic-on={domain}:{port}")
        else: 
            pass # TODO - do we need to force quic on other endpoints?
        
        if qlog:
            qlog_dir = f"{os.getcwd()}/results/qlogs/sync-{expnt_id}/edge/"
            edge_args.append(f"--log-net-log={qlog_dir}/{run_id}.json")
    # attempt to launch browser
    try:
        if pcap:
            pcap_file = f"{os.getcwd()}/results/packets/sync-{expnt_id}/edge/{run_id}-{h3}.keys"
            return pw_instance.chromium.launch(
                headless=True,
                executable_path='/opt/microsoft/msedge-dev/msedge',
                args=edge_args,
                env={"SSLKEYLOGFILE": pcap_file}
            )
        else:
            return pw_instance.chromium.launch(
                headless=True,
                executable_path='/opt/microsoft/msedge-dev/msedge',
                args=edge_args,
            )
    except Exception as e:  # if browser fails to launch, stop this request and write to the database
        logger.error(str(e))
        return None
    
"""
Get the navigation timing result, after going to the specified url, and retriving the desired file
from the server
"""
def get_results_sync(
    browser,
    h3: bool,
    endpoint: Endpoint,
    warmup: bool,
) -> json:
    # set up the browser context and page
    context = browser.new_context()
    page = context.new_page()
    url = endpoint.get_url()
    logger.debug(f"Navigating to url: {url}")
    
    # warm up the browser
    warmup_if_specified_sync(page, url, warmup)
    # attempt to navigate to the url
    try:
        # set the timeout to be 1 min, because under some bad network condition,
        # connection and data transfer take longer
        page.set_default_timeout(60000)
        response = page.goto(url)
        # getting performance timing data
        # if we don't stringify and parse, things break
        timing_function = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
        performance_timing = json.loads(page.evaluate(timing_function))
        performance_timing['server'] = response.headers['server']
    except Exception as e:
        # if we run into error, write it in the database
        logger.error(str(e))
        performance_timing = {'error': str(e)}
        pass
    browser.close()
    return performance_timing

"""
Extract the domain from the given url
"""
def get_domain(url):
    if "https://" not in url:
        return url
    else:
        return url[8:]

"""
Warm up the browser given a browser page
"""
def warmup_if_specified_sync(
    playwright_page: "Page",
    url: str,
    warmup: bool,
) -> None: 
    if warmup:
        # "?<random_string>" forces browser to re-request data
        new_url = url + "?send_data_again"
        playwright_page.goto(new_url)
