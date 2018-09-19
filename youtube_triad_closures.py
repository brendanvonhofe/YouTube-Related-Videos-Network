# Author:  Brendan von Hofe
# Credits to Cheryl Dugas for initial script for accessing YouTube API

#  youtube_triad_closures.py searches YouTube for videos related to a seed video, 
#  builds graphs around it from two different time points, and finds triad closures between them.

# to run from terminal window:  
#      Edit config.json instead of passing arguments
#      python3 youtube_triad_closures.py

from apiclient.discovery import build      # use build function to create a service object

import argparse    #  need for parsing the arguments in the command line
import csv         #  need since search results will be contained in a .csv file
import unidecode   #  need for processing text fields in the search results

import itertools
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import json

# put your API key into the API_KEY field below, in quotes
API_KEY = ""

API_NAME = "youtube"
API_VERSION = "v3"       # this should be the latest version

def main():
    # Edit config.json instead of passing arguments to the python program
    with open("config.json", "r") as read_file:
        config = json.load(read_file)

    start_date = config['start_date']
    end_date = config['end_date']
    end_date2 = config['end_date2']
    video_id = config['video_id']
    video_title = config['video_title']
    num_results = config['num_results']
    viz = config['viz']

    print("\nBuilding graphs from {} using {} related videos\n".format(video_title, num_results))
    print("Both graphs pull videos published after {}".format(start_date))
    print("Earlier graph pulls videos published before {}".format(end_date))
    print("Later graph pulls videos published before {}\n".format(end_date2))

    Gb = nx.Graph()
    Ga = nx.Graph()

    youtube_graph(Gb, video_id, video_title, num_results, start_date, end_date)
    youtube_graph(Ga, video_id, video_title, num_results, start_date, end_date2)

    if(viz):
        print("Saving visualizations of both graphs (they're pretty big)\n")
        graph_and_save(Gb, 'graph_before.png')
        graph_and_save(Ga, 'graph_after.png')

    print("Finding triad closures")
    tc = find_triad_closures(Gb, Ga)
    if(len(tc) == 0):
        print("No triad closures occurred")
    else:
        for clo in tc:
            print(clo)

# calls a YouTube search with given parameters and saves results to the graph
def search_and_add(youtube, G, initial_id, initial_title, n_results, after, before):
    if(after is not None):
        search_response = youtube.search().list(relatedToVideoId=initial_id, part="id,snippet", maxResults=n_results, 
                                                publishedAfter=after, publishedBefore=before, type='video').execute()
    else:
        search_response = youtube.search().list(relatedToVideoId=initial_id, part="id,snippet", 
                                                maxResults=n_results, type='video').execute()
    
    videos = []
    
    # search for videos matching search term; write an output line for each
    for search_result in search_response.get("items", []):
        if search_result["id"]["kind"] == "youtube#video":
            title = search_result["snippet"]["title"]
            title = unidecode.unidecode(title)
            videoId = search_result["id"]["videoId"]
            videos.append((videoId, title))
            
    for i, t in videos:
        G.add_node(t)
        G.add_edge(initial_title, t)
        
    return videos

# Do one YouTube search and then call search_and_add on each of the results
def youtube_graph(G, initial_id, initial_title, n_results, after=None, before=None):  
    # YouTube API object
    youtube = build(API_NAME, API_VERSION, developerKey=API_KEY)
    
    # Initial search
    related = search_and_add(youtube, G, initial_id, initial_title, n_results, after, before)
            
    # Search on each of the results from the initial
    for i, t in related:
        search_and_add(youtube, G, i, t, n_results, after, before)    

# Create a visualization of the graph and save that file
def graph_and_save(G, savename):
    fig = plt.figure(1, figsize=(16,9))
    ax = plt.subplot(111)
    nx.draw_networkx(G, ax=ax)
    plt.savefig(savename)
    plt.close(fig)

# Find triads in a graph
def find_triads(G):
    triads = []
    # loop thru every node
    for node in G.nodes():
        # node needs two neighbors to have a potential triad
        if(len(G.edges(node)) >= 2):
            # check all combinations of two neighbors
            for e1, e2 in itertools.combinations(G.edges(node), 2):
                n1, n2 = e1[1], e2[1] # get the neighbor nodes
                if(n1 in G[n2]): # if the neighbors are neighbors of each other they are a triad
                    triad = set([node, n1, n2])
                    if(triad not in triads):
                        triads.append(triad)
    
    return triads

def find_triad_closures(g1, g2):
    # g2 necessarily needs to be a later state of the graph
    t1 = find_triads(g1)
    t2 = find_triads(g2)

    print("Found {} triads in the earlier graph and {} in the later".format(len(t1), len(t2)))
    
    potential_closures = []
    # since t2 has a larger date range, there will necessarily be more videos
    for t in t2:
        if(t not in t1):
            potential_closures.append(t)
            
    closures = []
    for pt in potential_closures:
        x,y,z = list(pt)[0], list(pt)[1], list(pt)[2]

        # Check that all the nodes in the potential closure existed in the early graph.
        try:
            g1[x]
            g1[y]
            g1[z]
        except:
            pass

        # Check if they were neighbors before the triad formed
        if(y in g1[x] and z in g1[x]):
            closures.append((pt, "New connection between {} and {}".format(y,z)))
        elif(x in g1[y] and z in g1[y]):
            closures.append((pt, "New connection between {} and {}".format(x,z)))
        elif(x in g1[z] and y in g1[z]):
            closures.append((pt, "New connection between {} and {}".format(x,y)))
            
    return closures


if __name__ == "__main__":
    main()