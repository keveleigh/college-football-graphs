#!/usr/bin/env python

"""
This scrapes college football team information from
ESPN and turns it into pretty graphs.

In order to use this, you will need to download bs4, pygraph, pygraphviz, and graphviz.

Team dictionary format: {Team Name: [ESPN ID, FBS/FCS, Wins, Losses, ImageURL, {Opponent1: Outcome1, Opponent2: Outcome2, ... , OpponentN: OutcomeN}, [Opponent1, Outcome1], [Opponent2, Outcome2], ... , [OpponentN, OutcomeN]]}
ID dictionary format: {ESPN ID: Team Name}

Command format: python graphs.py reuse year school division
"""

import urllib2
import re
import datetime
import sys
import ast
import os
import argparse
import pygraphviz as gv

from bs4 import BeautifulSoup as bs
from pygraph.classes.digraph import digraph
from pygraph.algorithms.minmax import shortest_path
from pygraph.readwrite.dot import write

allSchools = {}
allIDs = {}

powerFive = ['Boston College',
             'Clemson',
             'Duke',
             'Florida State',
             'Georgia Tech',
             'Louisville',
             'Miami (FL)',
             'North Carolina',
             'North Carolina State',
             'Pittsburgh',
             'Syracuse',
             'Virginia',
             'Virginia Tech',
             'Wake Forest',
             'Baylor',
             'Iowa State',
             'Kansas',
             'Kansas State',
             'Oklahoma',
             'Oklahoma State',
             'TCU',
             'Texas',
             'Texas Tech',
             'West Virginia',
             'Illinois',
             'Indiana',
             'Iowa',
             'Maryland',
             'Michigan',
             'Michigan State',
             'Minnesota',
             'Nebraska',
             'Northwestern',
             'Ohio State',
             'Penn State',
             'Purdue',
             'Rutgers',
             'Wisconsin',
             'Arizona',
             'Arizona State',
             'California',
             'Colorado',
             'Oregon',
             'Oregon State',
             'Stanford',
             'UCLA',
             'USC',
             'Utah',
             'Washington',
             'Washington State',
             'Alabama',
             'Arkansas',
             'Auburn',
             'Florida',
             'Georgia',
             'Kentucky',
             'LSU',
             'Mississippi State',
             'Missouri',
             'Ole Miss',
             'South Carolina',
             'Tennessee',
             'Texas A&M',
             'Vanderbilt']

def _format_schedule_url(year, idNum):
    """Format ESPN link to scrape individual records from."""
    return 'http://espn.go.com/college-football/team/schedule/_/id/' + idNum + '/year/' + str(year) + '/'

def scrape_links(school, espn_schedule):
    """Scrape ESPN's pages for data."""
    global allSchools
    
    url = urllib2.urlopen(espn_schedule)
    soup = bs(url.read(), ['fast', 'lxml'])

    record = soup.find('div', attrs={'id':'showschedule'})
    record = record.find_all(text=re.compile('\d{1,2}-\d{1,2}'))
    record = record[len(record)-1].string.encode('ascii')
    record = record.split(' ')
    record = record[0].split('-')
    
    ## Get wins
    allSchools[school].append(record[0])
    ## Get losses
    allSchools[school].append(record[1])

    image = soup.find("img", "teamimage floatleft")
    image = image["src"]
    image = re.split('[&]', image.encode('ascii'))
    image = image[0]
    allSchools[school].append(image)
 
    if not os.path.exists('logos/'):
        os.mkdir('logos/')

    if not os.path.isfile('logos/' + school + '.png'):
        imgData = urllib2.urlopen(image).read()
        f = open('logos/' + school + '.png', 'wb')
        f.write(imgData)
        f.close()

    ## Get opponents
    opponents = soup.find_all("li", "team-name");
    outcomes = soup.find_all("ul", re.compile('game-schedule'));
    allSchools[school].append({});
    
    i = 6;
    j = 1;
    for opp in opponents:
        tempName = re.split('[><]', opp.encode('ascii'));
        oppID = re.split('[/]', tempName[3]);
        if len(oppID) >= 8:
            oppID = oppID[7]
            if oppID in allIDs:
                oppName = allIDs[oppID]
            else:
                oppName = tempName[2]
                oppName = re.sub('&amp;', '&', oppName, flags=re.IGNORECASE)
        else:
            oppName = tempName[2]
            oppName = re.sub('&amp;', '&', oppName, flags=re.IGNORECASE)
        allSchools[school].append([oppName]);
        if(j < len(outcomes)):
            temp = re.split('[><]', outcomes[j].encode('ascii'));
            if temp[6] == 'W' or temp[6] == 'L':
                allSchools[school][i].append(temp[6]);
                allSchools[school][5][oppName] = temp[6]; # May cause issues when team is played twice
                i+=1;
                j+=2;
            elif temp[4] == 'Postponed':
                del allSchools[school][i];
                j+=2;

def get_schools():
    global allSchools
    global allIDs
    
    url = urllib2.urlopen('http://espn.go.com/college-football/teams')
    soup = bs(url.read(), ['fast', 'lxml'])
    school_links = soup.find_all(href=re.compile("football/team/_/"))
    
    for school in school_links[0:128]:
        schID = (school['href'].split('/')[7])
        school = unicode(school.string).replace(u'\xe9', 'e') # Thanks San Jose State, sometimes
        school = school.encode('ascii')
        allSchools[school] = [schID,'FBS']
        allIDs[schID] = school
    for school in school_links[128:]:
        schID = (school['href'].split('/')[7])
        school = school.string.encode('ascii')
        allSchools[school] = [schID,'FCS']
        allIDs[schID] = school

def generate_graph(school, division):
    global allSchools

    if not os.path.exists('charts/'):
        os.mkdir('charts/')

    dgr = digraph()
    items = allSchools.items()

    for key, value in items:
        if ((division == 'P5' and key in powerFive) or
            (division == 'FBS' and value[1] == 'FBS') or
            (division == 'G5' and key not in powerFive and value[1] == 'FBS') or
            (division == 'FCS' and value[1] == 'FCS') or
            (key == school)):
            dgr.add_node(key)

    for key, value in items:
        if ((division == 'P5' and key in powerFive) or
            (division == 'FBS' and value[1] == 'FBS') or
            (division == 'G5' and key not in powerFive and value[1] == 'FBS') or
            (division == 'FCS' and value[1] == 'FCS') or
            (key == school)):
            for team in value[6:]:
                oppName = team[0]
                if len(team) > 1:
                    if (team[1] == 'W' and oppName in allSchools and
                        ((division == 'P5' and oppName in powerFive) or
                        (division == 'FBS' and allSchools[oppName][1] == 'FBS') or
                        (division == 'G5' and oppName not in powerFive and allSchools[oppName][1] == 'FBS') or
                        (division == 'FCS' and allSchools[oppName][1] == 'FCS') or
                        (oppName == school))):
                        if not dgr.has_edge((key,oppName)):
                            dgr.add_edge((key,oppName))

    if school == 'All':
        graph = dgr
    else:
        span = shortest_path(dgr, school)[0]
        gst = digraph()
        gst.add_spanning_tree(span)
        graph = gst

    if not os.path.exists('logos/'):
        os.mkdir('logos/')

    for node in graph.nodes():
        if not os.path.isfile('logos/' + node + '.png'):
            imgData = urllib2.urlopen(allSchools[node][4]).read()
            f = open('logos/' + node + '.png', 'wb')
            f.write(imgData)
            f.close()
        graph.node_attr[node] = [('shape','none'),('label',' '),('height',1.5),('width',1.5),('fixedsize','true'),('image','logos/' + node + '.png'),('imagescale','true')]
    
    print "Schools not in graph: " + str(list(set(dgr.nodes()) - set(gst.nodes())))

    dot = write(graph)

##    if not os.path.exists('dots/'):
##        os.mkdir('dots/')
##        
##    f = open('dots/' + school + ' dot.txt', 'w')
##    f.write(dot)
##    f.close()

    if school.lower() == 'all':
        folder = ''
        school = 'All'
    elif division == 'FCS':
        folder = 'FCS ' + division.upper() + '/'
    elif school in powerFive:
        folder = 'P5 ' + division.upper() + '/'
    else:
        folder = 'G5 ' + division.upper() + '/'

    if not os.path.exists('charts/' + folder):
        os.mkdir('charts/' + folder)
    
    gvv = gv.AGraph(dot)
    gvv.layout(prog='dot')
    gvv.draw('charts/' + folder + school + ' ' + division.upper() + '.png')

def main():
    global allSchools

    parser = argparse.ArgumentParser()
    parser.add_argument('reuse', help='specify whether to use the cached data or scrape new data', choices=['reuse', 'scrape'], type=str)
    parser.add_argument('year', choices=[2014], help='four digit year', type=int)
    parser.add_argument('school', help='specify the school to generate the graph, in quotes. correct case required. all is allowed.', type=str)
    parser.add_argument('division', help='specify the division for the graph', choices=['All', 'FBS', 'P5', 'G5', 'FCS'], type=str)
    args = parser.parse_args()
        
    if args.reuse == 'reuse' and os.path.isfile('teams'+str(args.year)+'.txt'):
        f = open('teams'+str(args.year)+'.txt', 'r')
        allSchools = ast.literal_eval(f.read())
    elif args.reuse == 'reuse':
        print 'There isn\'t any cached data. Please scrape first.'
        return
    else:
        get_schools()
        for school in allSchools:
            print 'Scraping ' + school
            scrape_links(school, _format_schedule_url(args.year, allSchools[school][0]))
        f = open('teams'+str(args.year)+'.txt', 'w')
        f.write(str(allSchools))
        f.close()

    if args.school.lower() == 'all' and args.division == 'All':
        for school in allSchools:
            if allSchools[school][1] == 'FBS':
                print 'Generating graphs for ' + school
                generate_graph(school, 'FBS')
                generate_graph(school, 'P5')
                generate_graph(school, 'G5')
            elif allSchools[school][1] == 'FCS':
                print 'Generating graphs for ' + school
                generate_graph(school, 'FCS')
    elif args.school.lower() == 'all' and args.division in ['FBS','P5','G5']:
        for school in allSchools:
            if allSchools[school][1] == 'FBS':
                print 'Generating graphs for ' + school
                generate_graph(school, args.division)
    elif args.school.lower() == 'all' and args.division == 'FCS':
        for school in allSchools:
            if allSchools[school][1] == 'FCS':
                print 'Generating graphs for ' + school
                generate_graph(school, args.division)
    else:
        generate_graph(args.school, args.division)

if __name__ == '__main__':
    import time
    start = time.time()
    main()
    print time.time() - start, 'seconds'
