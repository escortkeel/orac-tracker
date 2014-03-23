#!/bin/bash

PRETTIFY=/home/junkbot/problem_tracker/prettify.py
STUDENTS=/home/junkbot/problem_tracker/STUDENTS
PROBLEMS=/home/junkbot/problem_tracker/PROBLEMS
TEMPLATE=/home/junkbot/problem_tracker/tracker_template.html
OUTPUT=/home/junkbot/public_html/tracker/index.html

$PRETTIFY $STUDENTS $PROBLEMS $TEMPLATE > $OUTPUT
