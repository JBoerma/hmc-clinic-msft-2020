# Intro
This folder contains all of our work with [WebPageTest](https://github.com/WPO-Foundation/webpagetest). 

# Todo 
1. Install Script for WebPageTest using Docker
2. Interact with Server API

# Notes on WebPageTest API

## Starting and Tracking a Request

Start a test with a GET request. The following starts a test with `bing.com`, one test run, and requests the response be in json. There are more options. 
```
http://localhost:4000/runtest.php?url=bing.com&runs=1&f=json
```
This will return a json file, describing a test. Important fields include

1. `json["data"]["testID"]`: Unique identifier for test
2. `json["data"]["jsonURL"]`: Url to view JSON results of test
3. `json["data"]["summaryCSV"]`: CSV with the same data. 

Keep polling the `jsonURL`, and wait until `jsonURL["statusTest"]` is `"Test Complete"`. Relevant data can be found in `jsonURL["data"]`.  