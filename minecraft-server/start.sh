#!/bin/bash
cd "$(dirname "$0")"
SESSION_NAME="purpur"
if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found. Install it via 'sudo apt install -y tmux' before running this script."
  exit 1
fi
while true; do
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$TIMESTAMP] Starting Purpur server..."
  tmux new-session -d -s "$SESSION_NAME" "exec java \
    -Xms16G -Xmx24G \
    -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:G1NewSizePercent=30 \
    -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M \
    -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 \
    -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 \
    -XX:G1MixedGCLiveThresholdPercent=85 -XX:G1RSetUpdatingPauseTimePercent=5 \
    -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 \
    -XX:+AlwaysPreTouch -XX:+UnlockExperimentalVMOptions \
    -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true \
    -Dcom.mojang.eula.agree=true -Dfile.encoding=UTF-8 \
    -jar purpur.jar nogui"
  tmux attach -t "$SESSION_NAME"
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "Server stopped gracefully."
  else
    echo "Server crashed (exit code $EXIT_CODE). Restarting in 10 seconds..."
  fi
  sleep 10
  tmux kill-session -t "$SESSION_NAME" >/dev/null 2>&1
  echo "Restarting server..."
done
