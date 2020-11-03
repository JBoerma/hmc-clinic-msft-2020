import subprocess, csv, json
from playwright import sync_playwright

# generated command line code
call = "sudo tc qdisc add dev lo root netem delay 100ms 10ms 25%"
reset = "sudo tc qdisc del dev lo root"

networkInterface = "lo"

timingParameters = [ 
    "startTime",
    # "unloadEventStart",
    # "unloadEventEnd",
    "fetchStart",
    "domainLookupStart",
    "domainLookupEnd",
    "connectStart", 
    "secureConnectionStart",
    "connectEnd", 
    "requestStart", 
    "responseStart", 
    "responseEnd",
    "domInteractive",  
    "domContentLoadedEventStart", 
    "domContentLoadedEventEnd", 
    "domComplete", 
    "loadEventStart",
    "loadEventEnd",
]

def main():   
    # Make sure server is running
    subprocess.run("sudo systemctl restart nginx.service".split())
    csvFile = "out.csv"
    # Setup data file headers
    with open(csvFile, 'w', newline='\n') as outFile:
        csvWriter = csv.writer(outFile)
        csvWriter.writerow(timingParameters)

    # run the same experiment 10 times over h3
    with sync_playwright() as p:
        print("HTTP/3:")
        for _ in range(10):
            runExperiment(call,reset, p, "firefox", csvFile, True)
        print("HTTP/2")
        # run the same experiment 10 times over h2
        for _ in range(10):
            runExperiment(call,reset, p, "firefox", csvFile, False) 

def writeData(data, csvFile):
    with open(csvFile, 'a+', newline='\n') as outFile:
        csvWriter = csv.DictWriter(outFile, fieldnames=timingParameters, extrasaction='ignore')
        csvWriter.writerow(data)

def launchBrowser (pwInstance, browerType, csvFile, url, h3):
    if browerType  ==  "firefox":
        launchFirefox(pwInstance, csvFile, url, h3)
    elif browerType  ==  "chromium":
        launchChromium(pwInstance, csvFile, url, h3)
    elif browerType  ==  "edge":
        launchEdge(pwInstance, csvFile, url, h3)

def launchFirefox(pwInstance, csvFile, url, h3):
    firefoxPrefs = {}
    if (h3):
        firefoxPrefs = {
            "network.http.http3.enabled":True,
            "network.http.http3.alt-svc-mapping-for-testing":"localhost;h3-29=:443",
            "privacy.reduceTimerPrecision":False
        }
    browser = pwInstance.firefox.launch(
        headless=True,
        firefoxUserPrefs=firefoxPrefs,
    )

    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url)
    print("Firefox: ",response.headers['version'])

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))

    writeData(performanceTiming, csvFile)
    browser.close()

def launchChromium(pwInstance, csvFile, url, h3):
    chromiumArgs = []
    if (h3):
        chromiumArgs = ["--enable-quic", "--origin-to-force-quic-on=localhost:443", "--quic-version=h3-29"]

    browser =  pwInstance.chromium.launch(
        headless=True,
        args=chromiumArgs,
    )
    context = browser.newContext()
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url)
    print("Chromium: ",response.headers()['version'])

    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))
    
    writeData(performanceTiming, csvFile)
    browser.close()

def launchEdge(pwInstance, csvFile, url, h3):
    edgeArgs = []
    if (h3) :
        edgeArgs = ["--enable-quic", "--origin-to-force-quic-on=localhost:443", "--quic-version=h3-29"]
    browser = pwInstance.chromium.launch(
        headless=True,
        executablePath='/opt/microsoft/msedge-dev/msedge',
        args=edgeArgs,
    )
    context = browser.newContext()
    page = context.newPage()
    response = page.goto(url)
    print("Edge: ",response.headers()['version'])
    
    # getting performance timing data
    # if we don't stringify and parse, things break
    timingFunction = '''JSON.stringify(window.performance.getEntriesByType("navigation")[0])'''
    performanceTiming = json.loads(page.evaluate(timingFunction))
    
    writeData(performanceTiming, csvFile)
    browser.close()
    
def runExperiment(call, reset, pwInstance, browserType, csvFile, h3):
    url = "https://localhost"

    runTcCommand(call)
    launchBrowser(pwInstance, browserType, csvFile, url, h3)
    runTcCommand(reset)


def runTcCommand(command : str):
    result = subprocess.run(command.split())
    if result.returncode > 0:
        print("Issue running TC!")
        print(result.args)
        print(result.stderr)
        print("--------------------------")

if __name__ == "__main__":
    main()