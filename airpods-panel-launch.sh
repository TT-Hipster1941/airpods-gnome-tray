#!/usr/bin/env bash
if ! pgrep -f "airpods-panel.py" > /dev/null; then
    /usr/bin/python3 "$HOME/.local/bin/airpods-panel.py" &
fi
