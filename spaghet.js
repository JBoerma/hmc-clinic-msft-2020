const { exec, execSync } = require('child_process');
const { firefox, chromium } = require('playwright');

// generated command line code
call = "sudo tc qdisc add dev lo root netem delay 100ms 10ms 25%";
reset = "sudo tc qdisc del dev lo root"

networkInterface = "lo";

runExperiment(call,reset,"firefox");

async function launchBrowser (browerType) {
  if (browerType  ==  "firefox" ) {
    await launchFirefox();
  } else if (browerType  ==  "chromium") {
    await launchChromium();
  } else if (browerType  ==  "edge") {
    await launchEdge();
  }
}

async function launchFirefox() {
  const ffbrowser = await firefox.launch({
    headless: true,
    firefoxUserPrefs: {
        "network.http.http3.enabled":true,
        "network.http.http3.alt-svc-mapping-for-testing":"localhost;h3-29=:443"
      }
  });
  const ffcontext = await ffbrowser.newContext();
  const ffpage = await ffcontext.newPage();
  ffpage.on('response', response =>
      console.log("Firefox: ",response.headers()['version'])); 
  await ffpage.goto("https://localhost");
  await ffpage.reload();

  // getting performance timing data
  // if we don't stringify and parse, things break
  const performanceTimingJson = await ffpage.evaluate(() => JSON.stringify(window.performance.timing))
  const performanceTiming = JSON.parse(performanceTimingJson)
  writeCSVFromPerformanceTiming([performanceTiming])

  await ffbrowser.close();
}

////////////////////////////////////
function writeCSVFromPerformanceTiming(perfTiming) {
  const createCsvWriter = require('csv-writer').createObjectCsvWriter;
  const csvWriter = createCsvWriter({
    path: 'out.csv',
    header: [
        {id: "navigationStart", title: "navigationStart"}, 
        {id: "unloadEventStart", title: "unloadEventStart"}, 
        {id: "unloadEventEnd", title: "unloadEventEnd"}, 
        {id: "redirectStart", title: "redirectStart"}, 
        {id: "redirectEnd", title: "redirectEnd"}, 
        {id: "fetchStart", title: "fetchStart"}, 
        {id: "domainLookupStart", title: "domainLookupStart"}, 
        {id: "domainLookupEnd", title: "domainLookupEnd"}, 
        {id: "connectStart", title: "connectStart"}, 
        {id: "connectEnd", title: "connectEnd"}, 
        {id: "secureConnectionStart", title: "secureConnectionStart"}, 
        {id: "requestStart", title: "requestStart"}, 
        {id: "responseStart", title: "responseStart"}, 
        {id: "responseEnd", title: "responseEnd"}, 
        {id: "domLoading", title: "domLoading"}, 
        {id: "domInteractive", title: "domInteractive"}, 
        {id: "domContentLoadedEventStart", title: "domContentLoadedEventStart"}, 
        {id: "domContentLoadedEventEnd", title: "domContentLoadedEventEnd"}, 
        {id: "domComplete", title: "domComplete"}, 
        {id: "loadEventStart", title: "loadEventStart"}, 
        {id: "loadEventEnd", title: "loadEventEnd"},     
    ]
  });

  csvWriter
    .writeRecords(perfTiming)
    .then(()=> console.log('The CSV file was written successfully'));
}


async function launchChromium() {
  const chrombrowser = await chromium.launch({
    headless: true,
    args: ["--enable-quic", "--origin-to-force-quic-on=localhost:443", "--quic-version=h3-29"],
  });
  const chromcontext = await chrombrowser.newContext();
  const chrompage = await chromcontext.newPage();
  chrompage.on('response', response => {
    console.log("Chromium: ",response.headers()['version']);
  });
  await chrompage.goto("https://localhost:443");
  await chrompage.reload();
  await chrombrowser.close();
}

async function launchEdge() {
  const edgebrowser = await chromium.launch({
    headless: true,
    executablePath: '/opt/microsoft/msedge-dev/msedge',
    args: ["--enable-quic", "--origin-to-force-quic-on=localhost:443", "--quic-version=h3-29"],
  });
  const edgecontext = await edgebrowser.newContext();
  const edgepage = await edgecontext.newPage();
  edgepage.on('response', response => {
    console.log("Edge: ",response.headers()['version']);
  });
  await edgepage.goto("https://localhost:443");
  await edgepage.reload();
  await edgebrowser.close();
}

// Note: .then *hopefully ensures synchronicity
async function runExperiment(call, reset, browserType) {
  await runTcCommand(call)
  await launchBrowser(browserType)
  await runTcCommand(reset)
}


async function runTcCommand(command) {
    await exec(command, (err, stdout, stderr) => {
        console.log("Running: " + command)
        // do
        if (err) {
            console.log("Node encountered an error")
            console.log(err)
            return;
        }
      
        // the *entire* stdout and stderr (buffered)
        console.log(`stdout: ${stdout}`);
        console.log(`stderr: ${stderr}`);
      });
}