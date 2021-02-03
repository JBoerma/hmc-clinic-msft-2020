import json, time

from experiment_utils import timing_parameters

async def launch_browser_async(
    pw_instance, 
    browser_type: str,
    url: str, 
    h3: bool,
    port: str,
):
    if browser_type  ==  "firefox":
        return await launch_firefox_async(pw_instance, url, h3, port)
    elif browser_type  ==  "chromium":
        return await launch_chromium_async(pw_instance, url, h3, port)
    elif browser_type  ==  "edge":
        return await launch_edge_async(pw_instance, url, h3, port)


async def launch_firefox_async(
    pw_instance, 
    url: str, 
    h3: bool,
    port: str,
):
    firefox_user_prefs = {}
    firefox_user_prefs["privacy.reduceTimerPrecision"] = False
    
    if h3:
        domain = url if "https://" not in url else url[8:]
        firefox_user_prefs["network.http.http3.enabled"] = True
        if '446' in port:
            firefox_user_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-27={port.split('/')[0]}"
        else:
            firefox_user_prefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-29={port.split('/')[0]}"


    return await pw_instance.firefox.launch(
        headless=True,
        firefox_user_prefs=firefox_user_prefs,
    )


async def launch_chromium_async(
    pw_instance, 
    url: str, 
    h3: bool,
    port: str,
):
    chromium_args = []
    if (h3):
        domain = url if "https://" not in url else url[8:]
        chromium_args = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]

    return await pw_instance.chromium.launch(
        headless=True,
        args=chromium_args,
    )


async def launch_edge_async(
    pw_instance, 
    url: str, 
    h3: bool,
    port: str,
):
    edge_args = []
    if (h3) :
        domain = url if "https://" not in url else url[8:]
        edge_args = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
    
    return await pw_instance.chromium.launch(
        headless=True,
        executable_path='/opt/microsoft/msedge-dev/msedge',
        args=edge_args,
    )


async def get_results_async(
    pw_instance,
    browser_name,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    browser = await launch_browser_async(
        pw_instance, browser_name, url, h3, port 
    )
    context = await browser.new_context()
    page = await context.new_page()

    cache_buster = f"?{round(time.time())}"
    await warmup_if_specified_async(page, url + port + cache_buster, warmup)
    try:
        response = await page.goto(url + port)
        # getting performance timing data
        # if we don't stringify and parse, things break
        timing_function = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
        timing_response = await page.evaluate(timing_function)

        performance_timing = json.loads(timing_response)
        performance_timing['server'] = response.headers['server']
    except:
        performance_timing = {timing : -1 for timing in timing_parameters}
        performance_timing['server'] = "Error"
    # close context, allowing next call to use same browser
    await context.close()

    return (performance_timing, browser)


async def warmup_if_specified_async(
    playwright_page: "Page",
    url: str,
    warmup: bool,
): 
    if warmup:
        cache_buster = url + "?send_data_again"
        await playwright_page.goto(cache_buster)