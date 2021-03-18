import json
import sys
from typing import List
from tqdm import tqdm
import re, os, time, glob

from experiment_utils import reset_condition, apply_condition

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
    url: str,
    port: str,
    payload: str,
    warmup: bool,
    qlog: bool,
    expnt_id: int,
) -> json:
    apply_condition(device, condition)
    results = launch_browser_sync(pw_instance, browser_type, url, h3, port, payload, warmup, qlog, expnt_id)
    reset_condition(device)

    return results

"""
Invoke the specified browser launch functions, return the navigation timing data
"""
def launch_browser_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    browser_type: str,
    url: str, 
    h3: bool,
    port: str,
    payload: str,
    warmup: bool,
    qlog: bool,
    expnt_id: int
) -> json:
    qlog_dir = f"{os.getcwd()}/results/qlogs/"
    if not os.path.exists(qlog_dir):
        os.mkdir(qlog_dir)
    if browser_type  ==  "firefox":
        return launch_firefox_sync(pw_instance, url, h3, port, payload, warmup, qlog, expnt_id)
    elif browser_type  ==  "chromium":
        return launch_chromium_sync(pw_instance, url, h3, port, payload, warmup, qlog, expnt_id)
    elif browser_type  ==  "edge":
        return launch_edge_sync(pw_instance, url, h3, port, payload, warmup, qlog, expnt_id)

"""
Launch the firefox browser
"""
def launch_firefox_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    payload: str,
    warmup: bool,
    qlog: bool,
    expnt_id: int,
) -> json:
    # set up firefox preference
    firefox_prefs = {}
    firefox_prefs["privacy.reduceTimerPrecision"] = False
    qlog_dir = f"{os.getcwd()}/results/qlogs/firefox"
    if h3:
        if qlog:
            firefox_prefs["network.http.http3.enable_qlog"] = True  # enable qlog
            qlog_path = set_up_qlogs_dir(qlog_dir, expnt_id)
        domain = get_domain(url)
        firefox_prefs["network.http.http3.enabled"] = True # enable h3 protocol
        # the caddy server works with a different h3 version than the rest of the servers
        if '446' in port:
            firefox_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-27={port.split('/')[0]}"
        else:
            firefox_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-29={port.split('/')[0]}"
    # attempt to launch browser
    try:
        browser = pw_instance.firefox.launch(
            headless=True,
            firefox_user_prefs=firefox_prefs,
        )
        if h3 and qlog:
            # change qlogś name so that it will be saved to results/qlogs/firefox/[experimentID]
            for qlog in glob.glob("/tmp/qlog_*/*.qlog", recursive=True):
                os.rename(qlog, f"{qlog_path}/{time.time()}.qlog")
    except:  # if browser fails to launch, stop this request and write to the database
        return {"error": "launch_browser_failed"}
    # if browser successfully launches, get the navigation timing result
    return get_results_sync(browser, url, h3, port, payload, warmup)

"""
Launch the chromium browser
"""
def launch_chromium_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    payload: str,
    warmup: bool,
    qlog: bool,
    expnt_id: int,
) -> json:
    chromium_args = []
    if h3:
        # set up chromium arguments for enabling h3, qlog, h3 version
        domain = get_domain(url)
        chromium_args = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
        if qlog:
            # set up a directory results/qlogs/chromium/[experimentID] to save qlog
            qlog_dir = f"{os.getcwd()}/results/qlogs/chromium"
            qlog_path = set_up_qlogs_dir(qlog_dir, expnt_id)
            chromium_args.append(f"--log-net-log={qlog_path}/{time.time()}.json")
    # attempt to launch browser
    try:
        browser =  pw_instance.chromium.launch(
            headless=True,
            args=chromium_args,
        )
    except:  # if browser fails to launch, stop this request and write to the database
        return {"error":"launch_browser_failed"}
    # if browser successfully launches, get the navigation timing result
    return get_results_sync(browser, url, h3, port, payload, warmup)

"""
Launch the edge browser
"""
def launch_edge_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    payload: str,
    warmup: bool,
    qlog: bool,
    expnt_id: int,
) -> json:
    edge_args = []
    if (h3) :
        domain = get_domain(url)
        edge_args = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
        if qlog:
            qlog_dir = f"{os.getcwd()}/results/logs/edge"
            qlog_path = set_up_qlogs_dir(qlog_dir, expnt_id)
            edge_args.append(f"--log-net-log={qlog_path}/{time.time()}.json")
    # attempt to launch browser
    try:
        browser = pw_instance.chromium.launch(
            headless=True,
            executable_path='/opt/microsoft/msedge-dev/msedge',
            args=edge_args,
        )
    except:  # if browser fails to launch, stop this request and write to the database
        return {"error":"launch_browser_failed"}
    # if browser successfully launches, get the navigation timing result
    return get_results_sync(browser, url, h3, port, payload, warmup)
    
"""
Get the navigation timing result, after going to the specified url, and retriving the desired file
from the server
"""
def get_results_sync(
    browser,
    url: str, 
    h3: bool,
    port: str,
    payload: str,
    warmup: bool,
) -> json:
    # set up the browser context and page
    context = browser.new_context()
    page = context.new_page()
    tqdm.write( f"sync 131 {payload}")
    # use regular expression to check the format of the url
    regex = re.compile(r"\.\D+")
    if not regex.findall(url):
        # if url is not `xxx.xxx`, then it will be to our servers
        # ie: localhost, server ip address
        # then we can test specified h3 implementation or payload
        url = url + port + "/" + payload + ".html"
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
        tqdm.write(str(e))
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
Set up dirctory for qlogs, given parent directory and experiment id
"""
def set_up_qlogs_dir(qlog_dir, expnt_id):
    if not os.path.exists(qlog_dir):
        os.mkdir(qlog_dir)
    if not os.path.exists(f"{qlog_dir}/{expnt_id}"):
        os.mkdir(f"{qlog_dir}/{expnt_id}")
    return f"{qlog_dir}/{expnt_id}"

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
