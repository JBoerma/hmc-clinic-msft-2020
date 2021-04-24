import json
import sys
from typing import List
from tqdm import tqdm
import re, os, time, glob, asyncio

from experiment_utils import reset_condition, apply_condition
from endpoint import Endpoint

import logging
logger = logging.getLogger('__main__.' + __name__)

"""
Sets up asynchronous execution of the run
and returns the input parameters used so that
they can be recorded.
"""
def do_single_run_async(
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
    run_id: int
) -> json:
    task = asyncio.create_task(
            launch_browser_async(
                pw_instance, browser_type, h3, endpoint, warmup,
                qlog, pcap, expnt_id, run_id
            )
    )
    combo = (condition, endpoint, browser_type, h3)
    return (task, combo)

"""
Invoke the specified browser launch functions, return the navigation timing data
"""
async def launch_browser_async(
    pw_instance: "AsyncPlaywrightContextManager", 
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
        browser = await launch_firefox_async(pw_instance, h3, endpoint, warmup, qlog, pcap, expnt_id, run_id)
    elif browser_type  ==  "chromium":
        browser = await launch_chromium_async(pw_instance, h3, endpoint, warmup, qlog, pcap, expnt_id, run_id)
    elif browser_type  ==  "edge":
        browser = await launch_edge_async(pw_instance, h3, endpoint, warmup, qlog, pcap, expnt_id, run_id)
    # if browser fails to launch, stop this request and write to the database
    if not browser: 
        return {"error": "launch_browser_failed"}

    result = await get_results_async(browser, h3, endpoint, warmup)
    asyncio.create_task(browser.close())
    return result
"""
Launch the firefox browser
"""
async def launch_firefox_async(
    pw_instance: "AsyncPlaywrightContextManager", 
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
        firefox_prefs["network.http.spdy.enabled.http2"] = False # disable h2 protocol
        # the openlightspeed server works with a different h3 version than the rest of the servers

        port = endpoint.get_port()
        h3_version = "29"
        if endpoint.get_endpoint() == "server-openlitespeed":
            h3_version = "27"
        firefox_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{endpoint.port};h3-{h3_version}=:{port}"       
    # attempt to launch browser
    try:
        if pcap:
            pcap_file = f"{os.getcwd()}/results/packets/async-{expnt_id}/firefox/{run_id}-{h3}.keys"
            return await pw_instance.firefox.launch(
                headless=True,
                firefox_user_prefs=firefox_prefs,
                env={"SSLKEYLOGFILE": pcap_file}
            )
        else:
            return await pw_instance.firefox.launch(
                headless=True,
                firefox_user_prefs=firefox_prefs,
            )
    except Exception as e:  # if browser fails to launch, stop this request and write to the database
        logger.exception(str(e))
        return None

"""
Launch the chromium browser
"""
async def launch_chromium_async(
    pw_instance: "AsyncPlaywrightContextManager", 
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
        chromium_args = ["--enable-quic", "--quic-version=h3-29", "--disable-http2"]
        domain = endpoint.get_domain()
        port = endpoint.get_port()
        chromium_args.append(f"--origin-to-force-quic-on={domain}:{port}")
        if qlog:
            # set up a directory results/qlogs/chromium/[experimentID] to save qlog
            qlog_dir = f"{os.getcwd()}/results/qlogs/async-{expnt_id}/chromium/"
            chromium_args.append(f"--log-net-log={qlog_dir}/{run_id}.netlog")
    # attempt to launch browser
    try:
        if pcap:
            pcap_file = f"{os.getcwd()}/results/packets/async-{expnt_id}/chromium/{run_id}-{h3}.keys"
            return await pw_instance.chromium.launch(
                headless=True,
                args=chromium_args,
                env={"SSLKEYLOGFILE": pcap_file}
            )
        else:
            return await pw_instance.chromium.launch(
                headless=True,
                args=chromium_args,
            )
    except Exception as e:  # if browser fails to launch, stop this request and write to the database
        logger.error(str(e))
        return None

"""
Launch the edge browser
"""
async def launch_edge_async(
    pw_instance: "AsyncPlaywrightContextManager", 
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
        edge_args = ["--enable-quic", "--quic-version=h3-29", "--disable-http2"]
        domain = endpoint.get_domain()
        port = endpoint.get_port()
        edge_args.append(f"--origin-to-force-quic-on={domain}:{port}")
        if qlog:
            qlog_dir = f"{os.getcwd()}/results/async-qlogs/{expnt_id}/edge/"
            edge_args.append(f"--log-net-log={qlog_dir}/{run_id}.netlog")
    # attempt to launch browser
    try:
        if pcap:
            pcap_file = f"{os.getcwd()}/results/packets/async-{expnt_id}/edge/{run_id}-{h3}.keys"
            return await pw_instance.chromium.launch(
                headless=True,
                executable_path='/opt/microsoft/msedge-dev/msedge',
                args=edge_args,
                env={"SSLKEYLOGFILE": pcap_file}
            )
        else:
            return await pw_instance.chromium.launch(
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
async def get_results_async(
    browser,
    h3: bool,
    endpoint: Endpoint,
    warmup: bool,
) -> json:
    # set up the browser context and page
    context = await browser.new_context()
    page = await context.new_page()
    url = endpoint.get_url()
    logger.debug(f"Navigating to url: {url}")
    
    # warm up the browser
    await warmup_if_specified_async(page, url, warmup)
    # attempt to navigate to the url
    try:
        # set the timeout to be 1 min, because under some bad network condition,
        # connection and data transfer take longer
        page.set_default_timeout(60000)
        response = await page.goto(url)
        # getting performance timing data
        # if we don't stringify and parse, things break
        timing_function = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
        performance_timing = json.loads(await page.evaluate(timing_function))
        performance_timing['server'] = response.headers['server']
        if response.status == 404:
            logger.error("404 Response Code")
            performance_timing = {'error': '404'}
            pass
    except Exception as e:
        # if we run into error, write it in the database
        logger.error(str(e))
        performance_timing = {'error': str(e)}
        pass
    await browser.close()
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
async def warmup_if_specified_async(
    playwright_page: "Page",
    url: str,
    warmup: bool,
) -> None: 
    if warmup:
        # "?<random_string>" forces browser to re-request data
        new_url = url + "?send_data_again"
        playwright_page.goto(new_url)
