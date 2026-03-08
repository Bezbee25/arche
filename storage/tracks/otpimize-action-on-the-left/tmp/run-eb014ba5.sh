#!/bin/bash
claude --model claude-haiku-4-5-20251001 --allowedTools Read,Write,Edit,Bash < storage/tracks/otpimize-action-on-the-left/tmp/prompt-fd0b71e8-ead5b660.txt
_EXIT=$?
rm -f storage/tracks/otpimize-action-on-the-left/tmp/prompt-fd0b71e8-ead5b660.txt
rm -f storage/tracks/otpimize-action-on-the-left/tmp/run-eb014ba5.sh
[ $_EXIT -eq 0 ] && arche task done 2>/dev/null && echo '\n✓ Task marked as done.'
