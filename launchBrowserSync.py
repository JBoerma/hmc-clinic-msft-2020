import json
from typing import List

from experiment_utils import run_tc_command


def do_single_experiment_sync(
    call: str, 
    reset: str, 
    pw_instance: "SyncPlaywrightContextManager", 
    browser_type: str, 
    h3: bool,
    url: str,
    port: str,
    warmup: bool,
) -> json:
    run_tc_command(call)
    results = launch_browser_sync(pw_instance, browser_type, url, h3, port, warmup=warmup)
    run_tc_command(reset)

    return results


def launch_browser_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    browser_type: str,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    if browser_type  ==  "firefox":
        return launch_firefox_sync(pw_instance, url, h3, port, warmup)
    elif browser_type  ==  "chromium":
        return launch_chromium_sync(pw_instance, url, h3, port, warmup)
    elif browser_type  ==  "edge":
        return launch_edge_sync(pw_instance, url, h3, port, warmup)


def launch_firefox_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    firefox_prefs = {}
    firefox_prefs["privacy.reduceTimerPrecision"] = False
    
    if h3:
        domain = url if "https://" not in url else url[8:]
        firefox_prefs["network.http.http3.enabled"] = True
        firefox_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-29={port.split('/')[0]}"

    browser = pw_instance.firefox.launch(
        headless=True,
        firefox_user_prefs=firefox_prefs,
    )
    return get_results_sync(browser, url, h3, port, warmup)


def launch_chromium_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    chromium_args = []
    if (h3):
        domain = url if "https://" not in url else url[8:]
        chromium_args = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]

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
    return get_results_sync(browser, url, h3, port, warmup)


def launch_edge_sync(
    pw_instance: "SyncPlaywrightContextManager", 
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    edge_args = []
    if (h3) :
        domain = url if "https://" not in url else url[8:]
        edge_args = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
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
    return get_results_sync(browser, url, h3, port, warmup)
    

def get_results_sync(
    browser,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    context = browser.new_context()
    page = context.new_page()
    warmup_if_specified_sync(page, url + port, warmup)
    response = page.goto(url + port)

    # getting performance timing data
    # if we don't stringify and parse, things break
    timing_function = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performance_timing = json.loads(page.evaluate(timing_function))
    performance_timing['server'] = response.headers['server']
    
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