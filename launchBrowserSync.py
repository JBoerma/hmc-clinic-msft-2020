import json
from typing import List

from experiment_utils import run_tc_command


def do_single_experiment_sync(
    call: str, 
    reset: str, 
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str, 
    h3: bool,
    url: str,
    port: str,
    warmup: bool,
) -> json:
    run_tc_command(call)
    results = launch_browser_sync(pwInstance, browserType, url, h3, port, warmup=warmup)
    run_tc_command(reset)

    return results


def launch_browser_sync(
    pwInstance: "SyncPlaywrightContextManager", 
    browserType: str,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    if browserType  ==  "firefox":
        return launch_firefox_sync(pwInstance, url, h3, port, warmup)
    elif browserType  ==  "chromium":
        return launch_chromium_sync(pwInstance, url, h3, port, warmup)
    elif browserType  ==  "edge":
        return launch_edge_sync(pwInstance, url, h3, port, warmup)


def launch_firefox_sync(
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
    return get_results_sync(browser, url, h3, port, warmup)


def launch_chromium_sync(
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
    return get_results_sync(browser, url, h3, port, warmup)


def launch_edge_sync(
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
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))
    performanceTiming['server'] = response.headers['server']
    
    browser.close()
    return performanceTiming


def warmup_if_specified_sync(
    playwrightPage: "Page",
    url: str,
    warmup: bool,
) -> None: 
    if warmup:
        # "?<random_string>" forces browser to re-request data
        new_url = url + "?send_data_again"
        playwrightPage.goto(new_url)