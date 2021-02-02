import json, time

from experiment_utils import timingParameters

async def launch_browser_async(
    pwInstance, 
    browserType: str,
    url: str, 
    h3: bool,
    port: str,
):
    if browserType  ==  "firefox":
        return await launch_firefox_async(pwInstance, url, h3, port)
    elif browserType  ==  "chromium":
        return await launch_chromium_async(pwInstance, url, h3, port)
    elif browserType  ==  "edge":
        return await launch_edge_async(pwInstance, url, h3, port)


async def launch_firefox_async(
    pwInstance, 
    url: str, 
    h3: bool,
    port: str,
):
    firefoxPrefs = {}
    firefoxPrefs["privacy.reduceTimerPrecision"] = False
    
    if h3:
        domain = url if "https://" not in url else url[8:]
        firefoxPrefs["network.http.http3.enabled"] = True
        if '446' in port:
            firefoxPrefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-27={port.split('/')[0]}"
        else:
            firefoxPrefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-29={port.split('/')[0]}"


    return await pwInstance.firefox.launch(
        headless=True,
        firefox_user_prefs=firefoxPrefs,
    )


async def launch_chromium_async(
    pwInstance, 
    url: str, 
    h3: bool,
    port: str,
):
    chromiumArgs = []
    if (h3):
        domain = url if "https://" not in url else url[8:]
        chromiumArgs = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]

    return await pwInstance.chromium.launch(
        headless=True,
        args=chromiumArgs,
    )


async def launch_edge_async(
    pwInstance, 
    url: str, 
    h3: bool,
    port: str,
):
    edgeArgs = []
    if (h3) :
        domain = url if "https://" not in url else url[8:]
        edgeArgs = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
    
    return await pwInstance.chromium.launch(
        headless=True,
        executable_path='/opt/microsoft/msedge-dev/msedge',
        args=edgeArgs,
    )


async def get_results_async(
    browser,
    url: str, 
    h3: bool,
    port: str,
    warmup: bool,
) -> json:
    context = await browser.new_context()
    page = await context.new_page()

    cache_buster = f"?{round(time.time())}"
    await warmup_if_specified_async(page, url + port, warmup)
    try: 
        response = await page.goto(url + port + cache_buster)
        # getting performance timing data
        # if we don't stringify and parse, things break
        timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
        timingResponse = await page.evaluate(timingFunction)

        performanceTiming = json.loads(timingResponse)
        performanceTiming['server'] = response.headers['server']
    except:
        performanceTiming = {timing : -1 for timing in timingParameters}
        performanceTiming['server'] = "Error"
    
    # close context, allowing next call to use same browser
    await context.close()

    return performanceTiming


async def warmup_if_specified_async(
    playwrightPage: "Page",
    url: str,
    warmup: bool,
): 
    if warmup:
        cache_buster = url + "?send_data_again"
        await playwrightPage.goto(cache_buster)