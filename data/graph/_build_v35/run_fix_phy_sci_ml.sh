#!/bin/bash
cd /Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn
nohup python3 data/graph/_build_v35/fix.py physics > data/graph/_build_v35/physics_fix.log 2>&1 &
PID1=$!
disown
nohup python3 data/graph/_build_v35/fix.py science > data/graph/_build_v35/science_fix.log 2>&1 &
PID2=$!
disown
nohup python3 data/graph/_build_v35/fix.py morality_law > data/graph/_build_v35/morality_law_fix.log 2>&1 &
PID3=$!
disown
echo "physics fix: $PID1"
echo "science fix: $PID2"
echo "morality_law fix: $PID3"
