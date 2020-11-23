import matplotlib.pyplot as plt 
import numpy as np
import pandas as pd
import argparse


def cleanData(cvsFile):
    # original_data = np.genfromtxt(cvsFile, delimiter=',', 
    #                              dtype=[int,object, object, object, float,
    #                                     float, float, float, float,
    #                                     float, float, float, float,
    #                                     float, float, float, float,
    #                                     float, float, float],
    #                              comments = None)
    original_data = pd.read_csv(cvsFile)
    h3_data = original_data[original_data["httpVersion"]=="h3"]
    h2_data = original_data[original_data["httpVersion"]=="h2"]
    return h3_data, h2_data

def processData(data):
    app_fetch = data.domainLookupStart - data.fetchStart
    dnc = data.domainLookupEnd - data.domainLookupStart
    secure_connection_start = data.secureConnectionStart - data.connectStart
    tcp_connection = data.connectEnd - data.connectStart
    request = data.responseStart - data.requestStart
    response = data.responseEnd - data.responseStart
    processing = data.domComplete - data.responseEnd
    onload = data.loadEventEnd - data.loadEventStart
    page_load = data.domInteractive - data.startTime
    return [app_fetch, dnc, secure_connection_start, tcp_connection, request, response, processing, onload, page_load]

# take a dataframe of one column, return a sorted numpy array
def sortData(data):
    data = data.to_numpy()
    data = np.sort(data)
    return data

def plotCDF(h3_data, h2_data, outputFileName, plotName):
    h3_data = sortData(h3_data)
    h2_data = sortData(h2_data)
    length = h3_data.size
    y = [i/length for i in range(length)]
    _, ax = plt.subplots()
    ax.scatter(h3_data, y, c = 'tab:purple', label='HTTP/3', linestyle='solid')
    ax.scatter(h2_data, y, c = 'tab:olive', label= 'HTTP/2', linestyle='solid')
    plt.xlabel('Time (ms)')
    plt.ylabel('Percentile')
    plt.title('Cumulative Distribution of '+plotName)

    ax.legend()
    plt.savefig(outputFileName+plotName+'png')

def main(args):
    dataList = args.dir
    outputList = args.output

    for i, data in enumerate(dataList):
        h3_data, h2_data = cleanData(data)

        h3_event_data = processData(h3_data)
        h2_event_data = processData(h2_data)
        
        for j, event in enumerate(['App_Fetch', 'DNC_Lookup', 'Secure_Connection_Start', 'TCP_Connection', 'Request', 'Response', 'Processing', 'Onload', 'Page_Load']):

            plotCDF(h3_event_data[j], h2_event_data[j], outputList[i], event)
        
        # timingParameters = [
        # "startTime",
        # "fetchStart",
        # "domainLookupStart",
        # "domainLookupEnd",
        # "connectStart", 
        # "secureConnectionStart",
        # "connectEnd", 
        # "requestStart", 
        # "responseStart", 
        # "responseEnd",
        # "domInteractive",  
        # "domContentLoadedEventStart", 
        # "domContentLoadedEventEnd", 
        # "domComplete", 
        # "loadEventStart",
        # "loadEventEnd"
        # ]

        # color = ['c','m','y','r','g','b','tab:blue', 
        # 'tab:orange','tab:green','tab:red','tab:purple','tab:pink','tab:gray',
        # 'tab:olive','tab:cyan','k', 'tab:brown']

        # # this array helps visualize the data by separating different event actions
        # normalized_x = range(16)

        # # make a plot with time events
        # fig,ax = plt.subplots()


        # ax.scatter(normalized_x, normalized_h2,marker ='d', s=100, c = 'tab:purple', label='HTTP/2', linestyle='solid')
        # ax.scatter(normalized_x, normalized_h3,marker ='^', s=100, c = 'tab:olive', label= 'HTTP/3', linestyle='solid')
        # ax.plot(normalized_x, normalized_h2, c = 'tab:purple')
        # ax.plot(normalized_x, normalized_h3, c = 'tab:olive')

        # # add ticks on x axis to label navigation events
        # plt.xticks(np.arange(16),timingParameters, rotation = 'vertical' )
        # for ticklabel, tickcolor in zip(plt.gca().get_xticklabels(), color):
        #     ticklabel.set_color(tickcolor)

        # # adjust the bottom so the event name will not be cropped
        # plt.gcf().subplots_adjust(bottom = 0.5)

        # # label the graphs
        # plt.xlabel('Navigation Events')
        # plt.ylabel('Time (ms)')
        # plt.title('Navigation Timing of Fetching Nginx Server Homepage')

        # ax.legend()

        # plt.savefig(outputList[i])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="basic vitualization for data specified")
    parser.add_argument("--dir", "-d", metavar = "FILE", required = True, action = "append",
                        # type = argparse.FileType('r'),
                        help = "read data from FILE")
    parser.add_argument("--output", "-o", metavar="FILE", required=True, action = "append",
                        # type = argparse.FileType('wb'),
                        help="save output to FILE")
    args = parser.parse_args()
    main(args)