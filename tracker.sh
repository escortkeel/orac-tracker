#!/bin/bash

# Get the directory of this script
# see http://stackoverflow.com/questions/59895
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

PRETTIFY=$DIR/prettify.py
STUDENTS=$DIR/STUDENTS
PROBLEMS=$DIR/PROBLEMS
TEMPLATE=$DIR/tracker_template.html
OUTPUT=$HOME/public_html/tracker/index.html

$PRETTIFY $STUDENTS $PROBLEMS $TEMPLATE > $OUTPUT
