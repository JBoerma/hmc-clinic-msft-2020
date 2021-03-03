import json
import sys
from typing import List
from tqdm import tqdm
import re, os, time, glob

from experiment_utils import reset_condition, apply_condition

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
    qlog_path = f"{os.getcwd()}/results/qlogs/"
    if not os.path.exists(qlog_path):
        os.mkdir(qlog_path)
    if browser_type  ==  "firefox":
        return launch_firefox_sync(pw_instance, url, h3, port, payload, warmup, qlog, expnt_id)
    elif browser_type  ==  "chromium":
        return launch_chromium_sync(pw_instance, url, h3, port, payload, warmup, qlog, expnt_id)
    elif browser_type  ==  "edge":
        return launch_edge_sync(pw_instance, url, h3, port, payload, warmup, qlog, expnt_id)


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
    firefox_prefs = {}
    firefox_prefs["privacy.reduceTimerPrecision"] = False
    
    qlog_path = f"{os.getcwd()}/results/qlogs/firefox"
    if h3:
        if qlog:
            firefox_prefs["network.http.http3.enable_qlog"] = True
            if not os.path.exists(qlog_path):
                os.mkdir(qlog_path)
        domain = url if "https://" not in url else url[8:]
        firefox_prefs["network.http.http3.enabled"] = True
        if '446' in port:
            firefox_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-27={port.split('/')[0]}"
        else:
            firefox_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-29={port.split('/')[0]}"

    browser = pw_instance.firefox.launch(
        headless=True,
        firefox_user_prefs=firefox_prefs,
    )
    results = get_results_sync(browser, url, h3, port, payload, warmup)
    if h3 and qlog:
        if not os.path.exists(f"{qlog_path}/{expnt_id}"):
            os.mkdir(f"{qlog_path}/{expnt_id}")
        for qlog in glob.glob("/tmp/qlog_*/*.qlog", recursive=True):
            os.rename(qlog, f"{qlog_path}/{expnt_id}/{time.time()}.qlog")
    return results


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
    if (h3):
        domain = url if "https://" not in url else url[8:]
        chromium_args = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
        if qlog:
            qlog_path = f"{os.getcwd()}/results/qlogs/chromium"
            chromium_args.append(f"--log-net-log={qlog_path}/{expnt_id}/{time.time()}.json")
            if not os.path.exists(qlog_path):
                os.mkdir(qlog_path)
            if not os.path.exists(f"{qlog_path}/{expnt_id}"):
                os.mkdir(f"{qlog_path}/{expnt_id}")

    try:
        browser =  pw_instance.chromium.launch(
            headless=True,
            args=chromium_args,
        )
    except:
        browser =  pw_instance.chromium.launch(
            headless=True,
            args=chromium_args,
        )
    return get_results_sync(browser, url, h3, port, payload, warmup)


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
        domain = url if "https://" not in url else url[8:]
        edge_args = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
        if qlog:
            qlog_path = f"{os.getcwd()}/results/logs/edge"
            edge_args.append(f"--log-net-log={qlog_path}/{expnt_id}/{time.time()}.json")
            if not os.path.exists(qlog_path):
                os.mkdir(qlog_path)
            if not os.path.exists(f"{qlog_path}/{expnt_id}"):
                os.mkdir(f"{qlog_path}/{expnt_id}")
    try:
        browser = pw_instance.chromium.launch(
            headless=True,
            executable_path='/opt/microsoft/msedge-dev/msedge',
            args=edge_args,
        )
    except:
        browser = pw_instance.chromium.launch(
            headless=True,
            executable_path='/opt/microsoft/msedge-dev/msedge',
            args=edge_args,
        )
    return get_results_sync(browser, url, h3, port, payload, warmup)
    

def get_results_sync(
    browser,
    url: str, 
    h3: bool,
    port: str,
    payload: str,
    warmup: bool,
) -> json:
    context = browser.new_context()
    page = context.new_page()
    tqdm.write( f"sync 131 {payload}")
    regex = re.compile(r"\.\D+")
    if not regex.findall(url):
        url = url + port + "/" + payload + ".html"
    warmup_if_specified_sync(page, url, warmup)
    try:
        page.set_default_timeout(60000)
        response = page.goto(url)

        # getting performance timing data
        # if we don't stringify and parse, things break
        timing_function = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
        performance_timing = json.loads(page.evaluate(timing_function))
        performance_timing['server'] = response.headers['server']
    except Exception as e:
        tqdm.write(str(e))
        sys.exit() ## TODO - remove - this is for debugging
        timing_function = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
        performance_timing = json.loads(page.evaluate(timing_function))
        performance_timing['server'] = str(e)
        pass

    
    browser.close()
    return performance_timing


def warmup_if_specified_sync(
    playwright_page: "Page",
    url: str,
    warmup: bool,
) -> None: 
    if warmup:
        # "?<random_string>" forces browser to re-request data
        new_url = url + "?send_data_again"
        playwright_page.goto(new_url)
