from playwright import AsyncPlaywrightContextManager
from playwright.browser import Browser

async def launchBrowserAsync(
    pwInstance: AsyncPlaywrightContextManager, 
    browserType: str,
    url: str, 
    h3: bool,
    port: str,
) -> Browser:
    if browserType  ==  "firefox":
        return await launchFirefoxAsync(pwInstance, url, h3, port)
    elif browserType  ==  "chromium":
        return await launchChromiumAsync(pwInstance, url, h3, port)
    elif browserType  ==  "edge":
        return await launchEdgeAsync(pwInstance, url, h3, port)

async def launchFirefoxAsync(
    pwInstance: AsyncPlaywrightContextManager, 
    url: str, 
    h3: bool,
    port: str,
) -> Browser:
    firefoxPrefs = {}
    firefoxPrefs["privacy.reduceTimerPrecision"] = False
    
    if h3:
        domain = url if "https://" not in url else url[8:]
        firefoxPrefs["network.http.http3.enabled"] = True
        firefoxPrefs["network.http.http3.alt-svc-mapping-for-testing"] = f"{domain};h3-29={port.split('/')[0]}"

    return await pwInstance.firefox.launch(
        headless=True,
        firefoxUserPrefs=firefoxPrefs,
    )

async def launchChromiumAsync(
    pwInstance: AsyncPlaywrightContextManager, 
    url: str, 
    h3: bool,
    port: str,
) -> Browser:
    chromiumArgs = []
    if (h3):
        domain = url if "https://" not in url else url[8:]
        chromiumArgs = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]

    return await pwInstance.chromium.launch(
        headless=True,
        args=chromiumArgs,
    )

async def launchEdgeAsync(
    pwInstance: AsyncPlaywrightContextManager, 
    url: str, 
    h3: bool,
    port: str,
) -> Browser:
    edgeArgs = []
    if (h3) :
        domain = url if "https://" not in url else url[8:]
        edgeArgs = ["--enable-quic", f"--origin-to-force-quic-on={domain}:443", "--quic-version=h3-29"]
    
    return await pwInstance.chromium.launch(
        headless=True,
        executablePath='/opt/microsoft/msedge-dev/msedge',
        args=edgeArgs,
    )