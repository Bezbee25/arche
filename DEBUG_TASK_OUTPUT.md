 # Debugging Task Output in Terminals

## Problem
Task output is not appearing in dedicated terminals when running a task. The expected behavior is:
1. Click "▶ Run" on a task
2. A new terminal tab appears with name `-task-{taskId}`
3. Task output streams into that terminal in real-time
4. When done, "✓ Done" appears

## Current Issue
- Terminal tab may or may not appear
- No output appears in the terminal
- No error message shown to user

## Debugging Steps

### Step 1: Check Browser Console
1. Open the web interface
2. Open browser DevTools (F12 → Console tab)
3. Run a task
4. Look for logs starting with `[runTask]`:
   - `[runTask] Terminal created and selected: -task-{taskId}` ✓
   - `[runTask] Starting EventSource: /api/tracks/.../run...` ✓
   - `[runTask] EventSource opened successfully` ✓
   - `[runTask] Message received:...` (multiple lines) ✓

**If you don't see these logs**, the frontend code isn't executing. Check:
- Is the modal "Run Task" dialog appearing?
- Are you clicking the "▶ Run" button?
- Are there any JavaScript errors in the console?

### Step 2: Check Server Logs
1. Look at the server output where `arche web` is running
2. Look for logs starting with `[stream_task_run]`:
   - `[stream_task_run] Starting stream for task {taskId}...` ✓
   - `[stream_task_run] Creating subprocess: claude ...` ✓
   - `[stream_task_run] Subprocess created, writing X bytes...` ✓
   - `[stream_task_run] Starting to read from subprocess output...` ✓
   - `[stream_task_run] Yielding X bytes` (multiple lines) ✓
   - `[stream_task_run] EOF reached after N lines` ✓
   - `[stream_task_run] Process exited with code 0` ✓

**If stream doesn't start**:
- Check if `[stream_task_run] Starting stream...` appears
- If not, the endpoint wasn't called → check frontend logs

**If subprocess fails**:
- Check for error messages like:
  - `[stream_task_run] Exception: ...` → see full traceback
  - `CLI 'claude' not found` → install Claude CLI
  - Process exited with non-zero code → CLI error

### Step 3: Test the CLI Directly
If the subprocess fails, test if the `claude` CLI works:

```bash
# Test if claude CLI is installed
which claude

# Test a simple prompt
echo "Hello, what is 2+2?" | claude --output-format text
```

If this fails, you need to install the Claude CLI.

### Step 4: Check Network Traffic
1. Open browser DevTools → Network tab
2. Run a task
3. Look for request: `GET /api/tracks/{trackId}/tasks/{taskId}/run`
4. Click on it and check:
   - Status: `200` ✓ (not 404, 500, etc.)
   - Type: `EventStream` or `text/event-stream`
   - Response: Should show streaming data like `data: ...`

**If status is 500**: Check server logs for exception message

**If response is empty**: The subprocess produced no output

## Common Scenarios

### Scenario A: Terminal appears, but no output
- Stream is working, but subprocess isn't producing output
- Check if CLI is installed: `which claude`
- Check CLI version: `claude --version`
- Try running the CLI manually with a simple prompt

### Scenario B: Terminal doesn't appear at all
- Frontend isn't creating the terminal
- Check browser console for `[runTask]` logs
- If logs don't appear, the modal might not be opening correctly
- Try clicking the task row first to select it, then click "▶ Run"

### Scenario C: Error in terminal
- Look for `⚠ Connection error` or `⚠ Error: ...` messages
- Check browser console for error details
- Check server logs for exception traceback

## What the Logs Tell You

```
Browser Console:
[runTask] Terminal created and selected: -task-abc123
[runTask] Starting EventSource: /api/tracks/output/tasks/abc123/run...
[runTask] EventSource opened successfully
[runTask] Message received: Hello, this is the output...
[runTask] Message received: More output...
✓ Done (in terminal)

Server Console:
[stream_task_run] Starting stream for task abc123, cli=claude, model=claude-sonnet-4-6
[stream_task_run] Creating subprocess: claude claude-sonnet-4-6 ...
[stream_task_run] Subprocess created, writing 1234 bytes to stdin
[stream_task_run] Starting to read from subprocess output...
[stream_task_run] Yielding 45 bytes
[stream_task_run] Yielding 89 bytes
[stream_task_run] EOF reached after 2 lines
[stream_task_run] Process ended, waiting for exit...
[stream_task_run] Process exited with code 0
```

## If Still Stuck

If you've done all these steps and still can't see output:

1. **Collect logs**: Run a task and capture both browser console and server logs
2. **Check prerequisites**:
   - `which claude` → should return path
   - `claude --version` → should show version
   - `python -m arche init` → should work
3. **Restart everything**:
   - Kill the server process
   - Kill any remaining Python processes
   - Restart: `python -m arche web`
4. **Clear cache**:
   - Browser: Ctrl+Shift+Delete → Clear all
   - Disk: `rm -rf storage/tracks/*/sessions/`

## Next Steps

Once you've gathered the logs, we can:
1. Identify where the pipeline breaks
2. Fix the underlying issue
3. Remove the debug logs before committing

Good luck! 🔍
