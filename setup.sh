#!/bin/bash
# NoClaw Setup — delegates to setup.py
# Run: ./setup.sh  (or: python3 setup.py)
exec python3 "$(dirname "$0")/setup.py" "$@"
