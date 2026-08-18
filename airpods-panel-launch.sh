#!/usr/bin/env bash
if ! pgrep -f "airpods-panel.py" > /dev/null; then
    /usr/bin/python3 /home/spike/.local/bin/airpods-panel.py &
fi
