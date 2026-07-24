#!/bin/bash
cd /Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn
nohup python3 data/graph/_build_v35/build.py science > data/graph/_build_v35/science_build.log 2>&1 &
PID1=$!
disown
nohup python3 data/graph/_build_v35/build.py morality_law > data/graph/_build_v35/morality_law_build.log 2>&1 &
PID2=$!
disown
echo "science PID: $PID1"
echo "morality_law PID: $PID2"
