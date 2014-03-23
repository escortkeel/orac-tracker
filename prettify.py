#!/usr/bin/env python

DEBUG = True

import sys
import subprocess
import datetime

# database
DATABASE_NAME = "train"

# html template tags
SCOREBOARD_TAG = "{ scoreboard }"
ALL_SCOREBOARD_TAG = "{ all_scoreboard }"
RECENT_SUBMISSIONS_TAG = "{ recent_submissions }"
TIMESTAMP_TAG = "{ timestamp }"

# html display options
PROBLEM_NAME_COLSPAN = 14
SCORE_COLSPAN = 3

# number of recent submissions
NUM_RECENT_SUBMISSIONS = 20

def debug_print(s=''):
    if DEBUG:
        sys.stderr.write(repr(s) + "\n")

# score: < 0 for no attempt
def get_color_tag(score):
    if score < 0:
        return "score_no_attempt"
    elif score == 0:
        return "score_0"
    elif score == 100:
        return "score_100"
    else:
        score_band = (score/10)*10
        return ("score_%d_%d" % (score_band, score_band+10))

# given a tuple of (first_name, last_name) returns a formatted name string
def format_name(name_tuple):
    return ("%s %s" % (name_tuple[0], name_tuple[1])).title()

# given a list, makes a string fit for querying psql, eg
# ['abc','def','ghi'] -> "('abc','def','ghi')"
def psql_list_str(l):
    list_str = ','.join(map(lambda x: ("'%s'" % x), l))
    return ("(%s)" % list_str)

# returns tuples with the query string
def query(query_string):
    subproc_echo = subprocess.Popen(["echo", query_string], stdout=subprocess.PIPE)
    subproc_psql = subprocess.Popen(["psql", "--tuples-only", DATABASE_NAME],
                                     stdin=subproc_echo.stdout,
                                     stdout=subprocess.PIPE)
    subproc_echo.stdout.close()
    stdout, stderr = subproc_psql.communicate()
    stdout = stdout.split('\n')

    output = []
    for line in stdout:
        line = line.strip()
        if line != '':
            vals = line.split('|')
            for i in xrange(len(vals)):
                vals[i] = vals[i].strip()
            output.append(tuple(vals))

    return output

# returns a list of usernames
def get_users(students_file):
    return map(lambda x: x.strip(), students_file.read().split())

# returns a list of problem names
def get_problem_names(problems_file):
    return map(lambda x: x.strip(), problems_file.read().split())

# returns a dictionary: name [str] -> title [str]
def get_problem_title_mapping(problem_names):
    problem_name_str = psql_list_str(problem_names)
    query_string = "SELECT name, title FROM problems WHERE name in " + \
                   problem_name_str
    database_response = query(query_string)

    ret = {}
    for response in database_response:
        ret[response[0]] = response[1]

    return ret

# returns a dictionary: username [str] -> ( first_name [str], last_name [str] )
def get_name_tag_mapping(usernames):
    username_str = psql_list_str(usernames)
    query_str = "SELECT username, firstname, lastname " + \
                "FROM competitors WHERE username in " + \
                username_str
    database_response = query(query_str)

    ret = {}
    for response in database_response:
        ret[response[0]] = (response[1], response[2])

    return ret

# fetch scores for users across a set of problems; if this list of problems is
# empty, fetch all problems that have been submitted for
# returns a dictionary of (problem_name, username) -> max_mark
def get_scores(usernames, problem_names=[]):
    user_clause = "competitors.username in " + \
                psql_list_str(usernames)

    # allow for optional empty problem_names which fetches all submitted
    # problems
    if len(problem_names) > 0:
        problem_clause = "problems.name in " + \
                    psql_list_str(problem_names)
    else:
        problem_clause = "TRUE"

    query_string = "SELECT DISTINCT problems.name, competitors.username, " + \
                   "submissions.mark " + \
                   "FROM submissions " + \
                   "INNER JOIN competitors ON competitors.id = " + \
                   "submissions.competitorid " + \
                   "INNER JOIN problems ON submissions.problemid = " + \
                   "problems.id " \
                   "WHERE " + user_clause + " AND " + problem_clause + \
                   " AND submissions.mark IS NOT NULL " + \
                   "ORDER BY competitors.username, submissions.mark"
    database_response = query(query_string)

    ret = {}
    for response in database_response:
        key = (response[0], response[1])
        if key in ret:
            ret[key] = max(ret[key], int(response[2]))
        else:
            ret[key] = int(response[2])

    return ret

# returns the html for a table scoreboard
def make_scoreboard(usernames, name_tag_mapping, problem_names, problem_title_mapping, scores):
    html_rows = ""

    html_header_row = ""
    for i in xrange(len(usernames)+1):
        if i > 0:
            html_header_row += '<th colspan="%d" class="username">%s</th>\n' % \
                               (SCORE_COLSPAN,
                                format_name(name_tag_mapping[usernames[i-1]]))
        else:
            html_header_row += '<th colspan="%d"></th>\n' % \
                               (PROBLEM_NAME_COLSPAN)

    html_rows += '<thead><tr>\n%s</tr></thead>\n\n' % (html_header_row)

    for p in problem_names:
        html_this_row = ""

        problem_title = problem_title_mapping[p]
        html_this_row += '<td colspan="%d" class="problemtitle">%s</td>\n' % \
                         (PROBLEM_NAME_COLSPAN, problem_title)

        for u in usernames:
            key = (p, u)
    
            if key in scores:
                score = scores[key]
                score_str = str(score)
                tooltip_score_str = str(score)
            else:
                score = -1
                score_str = ""
                tooltip_score_str = "not attempted"

            color_tag = get_color_tag(score)

            preferred_name = format_name(name_tag_mapping[u])

            html_this_row += ('<td colspan="%d" class="score %s" ' + \
                             'title="%s, %s: %s">%s</td>\n') % \
                             (SCORE_COLSPAN, color_tag, preferred_name,
                              problem_title, tooltip_score_str, score_str)

        html_rows += '<tr class="problemrow">\n%s</tr>\n\n' % (html_this_row)

    html_table = '<table class="scoreboard">\n%s\n</table>\n' % (html_rows)

    return html_table

# returns a list of tuples of the form:
# (username [str], problem_title [str], score [str], timestamp [str])
def get_recent_submissions(usernames):
    user_clause = "c.username in " + psql_list_str(usernames)

    query_string = "SELECT c.username, p.title, s.mark, s.timestamp " + \
                   "FROM competitors c " + \
                   "JOIN submissions s on c.id = competitorid " + \
                   "JOIN problems p on p.id = s.problemid " + \
                   "WHERE " + user_clause + " " + \
                   "ORDER BY s.timestamp DESC " + \
                   ("LIMIT %d" % (NUM_RECENT_SUBMISSIONS))

    database_response = query(query_string)
    return database_response

# given a list of tuples of the form:
# (preferred_name [str], problem_title [str], score [int], timestamp [str])
# returns the html for the recent submissions table
def make_recent_submissions(submissions_tuples):
    html_rows = ""

    # make the html header
    html_header_row = ""
    html_header_row += "<th>Student</th>\n"
    html_header_row += "<th>Problem</th>\n"
    html_header_row += "<th>Score</th>\n"
    html_header_row += "<th>Timestamp</th>\n"
    html_rows += '<thead><tr>\n%s</tr></thead>\n\n' % (html_header_row)

    for s in submissions_tuples:
        # unpack
        name_tuple, problem_title, score, timestamp = s
        preferred_name = format_name(name_tuple)
        score = int(score)

        html_this_row = ""
        html_this_row += ('<td class="sub_data">%s</td>\n' % (preferred_name))
        html_this_row += ('<td class="sub_data">%s</td>\n' % (problem_title))

        color_tag = get_color_tag(score)
        html_this_row += ('<td class="%s sub_data score">%d</td>\n' % (color_tag, score))

        html_this_row += ('<td class="sub_data">%s</td>\n' % (timestamp))

        html_rows += ('<tr class="sub_data_row">\n%s</tr>\n\n' % (html_this_row))

    html_table = '<table id="recent_subs">\n%s\n</table>\n' % (html_rows)

    return html_table

def get_timestamp():
    timestamp = str(datetime.datetime.now())
    return timestamp

def main():
    # get files
    students_filename = sys.argv[1]
    students_file = open(students_filename, "r")

    problems_filename = sys.argv[2]
    problems_file = open(problems_filename, "r")

    tracker_template_filename = sys.argv[3]
    tracker_template_file = open(tracker_template_filename, "r")

    # get data from files
    usernames = get_users(students_file)
    problem_names = get_problem_names(problems_file)

    #################### SELECTED PROBLEMS #############################

    # get data from database required by data from files
    name_tag_mapping = get_name_tag_mapping(usernames)
    problem_title_mapping = get_problem_title_mapping(problem_names)
    scores = get_scores(usernames, problem_names)

    # make scoreboard! yay!
    html_table = make_scoreboard(usernames, name_tag_mapping,
                                 problem_names, problem_title_mapping,
                                 scores)

    #################### ALL PROBLEMS ##################################

    # get the usual data (just in a weird order)
    all_scores = get_scores(usernames)
    all_problem_names = list(set([key[0] for key in all_scores]))
    all_problem_title_mapping = get_problem_title_mapping(all_problem_names)

    # sort alphabetically!
    all_problem_names = sorted(all_problem_names,
                               key=lambda x: all_problem_title_mapping[x])

    all_html_table = make_scoreboard(usernames, name_tag_mapping,
                                     all_problem_names,
                                     all_problem_title_mapping,
                                     all_scores)

    #################### RECENT SUBMISSIONS #############################
    raw_recent_submissions = get_recent_submissions(usernames)
    recent_submissions = []

    # change raw usernames into preferred names
    for r in raw_recent_submissions:
        temp = list(r)
        raw_username = temp[0]
        preferred_name = name_tag_mapping[raw_username]
        temp[0] = preferred_name
        recent_submissions.append(tuple(temp))

    recent_submissions_html_table = make_recent_submissions(recent_submissions)

    # timestamp
    timestamp = get_timestamp()

    #################### DEBUG ##########################################
    # debug to make sure everything's working
    #debug_print( name_tag_mapping )
    #debug_print()
    #debug_print()

    #debug_print( problem_title_mapping )
    #debug_print()
    #debug_print()

    #debug_print( scores )
    #debug_print()
    #debug_print()

    #debug_print( html_table )
    #debug_print()
    #debug_print()

    # read template
    template = tracker_template_file.read()
    tracker_template_file.close()

    # replace template fields
    html_output = template
    html_output = html_output.replace( SCOREBOARD_TAG, html_table )
    html_output = html_output.replace( RECENT_SUBMISSIONS_TAG,
                                       recent_submissions_html_table )
    html_output = html_output.replace( ALL_SCOREBOARD_TAG, all_html_table )
    html_output = html_output.replace( TIMESTAMP_TAG, timestamp )

    print html_output

if __name__ == "__main__":
    main()
