#!/bin/bash
# V4.1.2 L2 视频续跑 loop
# 每轮跑 30 个, 跑完测速一次, 限速时停
# 退出条件: 视频数 >= 800 或连续 3 轮 0 进展

set -e
PROJECT=/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn
PY=$PROJECT/.venv/bin/python3
SCRIPT=$PROJECT/scripts/auto_pick_videos.py
TARGET=800
BATCH=30
SLEEP_BATCH=60   # 每批之间等 1 分钟, 让 B 站限速恢复
MAX_ROUNDS=15    # 最多 15 轮 (450 个)

cd "$PROJECT"

for i in $(seq 1 $MAX_ROUNDS); do
  cur=$(/usr/bin/plutil -convert json -o - "$PROJECT/web/data/videos.json" 2>/dev/null | $PY -c "import json,sys;d=json.load(sys.stdin);print(len(d.get('videos',[])))" 2>/dev/null || echo 0)
  if [ "$cur" -ge "$TARGET" ]; then
    echo "已达 $cur >= $TARGET, 退"
    break
  fi
  echo "=== round $i / $MAX_ROUNDS, 当前 $cur ==="
  timeout 600 $PY $SCRIPT 2>&1 | tail -40
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "exit $rc, 等 2 分钟再试"
    sleep 120
  else
    sleep $SLEEP_BATCH
  fi
done

echo "=== 跑完 ==="
$PY -c "
import json
d = json.load(open('web/data/videos.json'))
print(f'最终: {len(d[\"videos\"])} 视频')
"
