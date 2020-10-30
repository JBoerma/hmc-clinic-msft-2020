import matplotlib.pyplot as plt 
import numpy as np 

# read from out.csv into a numpy matrix
original_data = np.genfromtxt('out.csv', delimiter=',')

# the first 10 rows corresponds to 10 connections over h3
h3_data = original_data[1:11,:]

# the last 10 rows corresponds to 10 connections over h2
h2_data = original_data[11:, :]

# get the average of each column
normalized_h3 = np.mean(h3_data, axis = 0)
normalized_h2 = np.mean(h2_data, axis = 0)

timingParameters = [#"navigationStart",
# "unloadEventStart",
# "unloadEventEnd",
"startTime",
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
 "loadEventEnd"
]

color = ['c','m','y','r','g','b','tab:blue', 
'tab:orange','tab:green','tab:red','tab:purple','tab:pink','tab:gray',
'tab:olive','tab:cyan','k', 'tab:brown']

# this array helps visualize the data by separating different event actions
normalized_x = range(16)

# make a plot with time events
fig,ax = plt.subplots()


ax.scatter(normalized_x, normalized_h2,marker ='d', s=100, c = 'tab:purple', label='HTTP/2', linestyle='solid')
ax.scatter(normalized_x, normalized_h3,marker ='^', s=100, c = 'tab:olive', label= 'HTTP/3', linestyle='solid')
ax.plot(normalized_x, normalized_h2, c = 'tab:purple')
ax.plot(normalized_x, normalized_h3, c = 'tab:olive')

# add ticks on x axis to label navigation events
plt.xticks(np.arange(16),timingParameters, rotation = 'vertical' )
for ticklabel, tickcolor in zip(plt.gca().get_xticklabels(), color):
    ticklabel.set_color(tickcolor)

# adjust the bottom so the event name will not be cropped
plt.gcf().subplots_adjust(bottom = 0.5)

# label the graphs
plt.xlabel('Navigation Events')
plt.ylabel('Time (ms)')
plt.title('Navigation Timing of Fetching Nginx Server Homepage')

ax.legend()

plt.savefig('graph.png')
