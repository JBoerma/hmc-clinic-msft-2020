const { exec, execSync } = require('child_process');
const { timeStamp } = require('console');
const { firefox, chromium } = require('playwright');

// generated command line code
call = "sudo tc qdisc add dev lo root netem delay 100ms 10ms 25%";
reset = "sudo tc qdisc del dev lo root"

networkInterface = "lo";

timingParameters = 
[ "startTime",
  //"navigationStart",
// "unloadEventStart",
// "unloadEventEnd",
"fetchStart",
"domainLookupStart",
"domainLookupEnd",
"connectStart", 
"secureConnectionStart",
"connectEnd", 
"requestStart", 
"responseStart", 
 "responseEnd",
 //"domLoading", 
 "domInteractive",  
 "domContentLoadedEventStart", 
 "domContentLoadedEventEnd", 
 "domComplete", 
 "loadEventStart",
 "loadEventEnd"
];

(async ()=>{
  // because otherwise our server won't necessarily be running
  await exec(
    "sudo systemctl restart nginx.service",
    (err, stdout, stderr) => { }
  )
  const createCsvWriter = require('csv-writer').createObjectCsvWriter;
  const csvWriter = createCsvWriter({
    path: 'out.csv',
    append: false,
    header: 
    timingParameters.map(function(x){ return {id: x, title: x}})
  });

  // run the same experiment 10 times over h3
  console.log("HTTP/3:")
  for (let i = 0; i < 10; i++) {
    await runExperiment(call,reset,"firefox", csvWriter, true);
  }
  console.log("HTTP/2")
  // run the same experiment 10 times over h2
  for (let i = 0; i < 10; i++) {
    await runExperiment(call,reset,"firefox", csvWriter, false);
  } 

  // visualize the experiment using python (Todo: fix this!)
  await exec(
    "python3 visualization.py", (err, stdout, stderr) => { }
  )
})();

async function launchBrowser (browerType, csvWriter, h3 = true) {
  if (browerType  ==  "firefox" ) {
    await launchFirefox(csvWriter, h3);
  } else if (browerType  ==  "chromium") {
    await launchChromium(h3);
  } else if (browerType  ==  "edge") {
    await launchEdge(h3);
  }
}

async function launchFirefox(csvWriter, h3 = true) {
  let firefoxPrefs = {}
  if (h3) {
    firefoxPrefs = {
      "network.http.http3.enabled":true,
      "network.http.http3.alt-svc-mapping-for-testing":"localhost;h3-29=:443",
      "privacy.reduceTimerPrecision":false
    }
  }
  const ffbrowser = await firefox.launch({
    headless: true,
    firefoxUserPrefs: firefoxPrefs,
  });
  const ffcontext = await ffbrowser.newContext();
  const ffpage = await ffcontext.newPage();
  ffpage.on('response', response =>
      console.log("Firefox: ",response.headers()['version'])); 
  await ffpage.goto("https://localhost");
  //await ffpage.reload();

  // getting performance timing data
  // if we don't stringify and parse, things break
  //const performanceTimingJson = await ffpage.evaluate(() => JSON.stringify(window.performance.timing))
  const performanceTimingJson = await ffpage.evaluate(() => JSON.stringify(window.performance.getEntriesByType("navigation")[0]))
  const performanceTiming = JSON.parse(performanceTimingJson)
  console.log(performanceTiming)
  //await csvWriter.writeRecords([normalizePerformanceTiming(performanceTiming.navigationStart, performanceTiming) ])
  await csvWriter.writeRecords([performanceTiming])
    .then(()=> console.log('The CSV file was written successfully'));

  await ffbrowser.close();
}
// this function takes in a JSON object and subtract every field with navigationStart
function normalizePerformanceTiming(navigationStart, perfTiming) {
  let normalized = {}
  for (var field in perfTiming) {
    if (field != "redirectStart" || field != "redirectEnd") {
      let timeStamp = perfTiming[field]
      normalized[field] = timeStamp - navigationStart
    }
  }
  return normalized;
}
////////////////////////////////////

async function launchChromium(h3 = true) {
  let chromiumArgs = []
  if (h3) {
    chromiumArgs = ["--enable-quic", "--origin-to-force-quic-on=localhost:443", "--quic-version=h3-29"];
  }
  const chrombrowser = await chromium.launch({
    headless: true,
    args: chromiumArgs,
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

async function launchEdge(h3 = true) {
  let edgeArgs = []
  if (h3) {
    chromiumArgs = ["--enable-quic", "--origin-to-force-quic-on=localhost:443", "--quic-version=h3-29"];
  }
  const edgebrowser = await chromium.launch({
    headless: true,
    executablePath: '/opt/microsoft/msedge-dev/msedge',
    args: edgeArgs,
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
async function runExperiment(call, reset, browserType, csvWriter, h3 = true) {
  await runTcCommand(call)
  await launchBrowser(browserType, csvWriter, h3)
  await runTcCommand(reset)
}


async function runTcCommand(command) {
    await exec(command, (err, stdout, stderr) => {
    console.log("Running: " + command);
    // do
    if (err) {
      console.log("Node encountered an error");
      console.log(err);
      return;
    }

    // the *entire* stdout and stderr (buffered)
    console.log(`stdout: ${stdout}`);
    console.log(`stderr: ${stderr}`);
  });
}