"""WebSocket → pty terminal bridge using ptyprocess."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path

from fastapi.websockets import WebSocket, WebSocketDisconnect, WebSocketState


class TerminalManager:
    """Manages WebSocket ↔ pty sessions."""

    async def handle(self, websocket: WebSocket, init_cmd: str | None = None, cols: int = 220, rows: int = 50) -> None:
        await websocket.accept()

        try:
            import ptyprocess
        except ImportError:
            await websocket.send_text(
                "\r\n[arche] ptyprocess not installed. Run: pip install ptyprocess\r\n"
            )
            await websocket.close()
            return

        # Determine shell
        shell = os.environ.get("SHELL", shutil.which("bash") or "/bin/sh")

        cwd = str(Path.cwd())

        try:
            proc = ptyprocess.PtyProcess.spawn(
                [shell],
                cwd=cwd,
                dimensions=(rows, cols),
                env={
                    **os.environ,
                    "TERM": "xterm-256color",
                    "COLUMNS": str(cols),
                    "LINES": str(rows),
                },
            )
        except Exception as e:
            await websocket.send_text(f"\r\n[arche] Failed to start terminal: {e}\r\n")
            await websocket.close()
            return

        # Source arche into the shell path
        arche_dir = str(Path(__file__).parent.parent)

        async def read_pty():
            """Read from pty and send to WebSocket."""
            loop = asyncio.get_event_loop()
            while True:
                try:
                    data = await loop.run_in_executor(None, _read_pty_data, proc)
                    if data is None:
                        break
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_bytes(data)
                except Exception:
                    break

        async def write_pty():
            """Receive from WebSocket and write to pty.

            Text frames = JSON control messages (e.g. resize).
            Binary frames = raw keyboard input.
            """
            while True:
                try:
                    msg = await websocket.receive()
                    if msg.get("text"):
                        try:
                            ctrl = json.loads(msg["text"])
                            if ctrl.get("type") == "resize":
                                rows = max(1, int(ctrl.get("rows", 24)))
                                cols = max(1, int(ctrl.get("cols", 80)))
                                proc.setwinsize(rows, cols)
                        except (json.JSONDecodeError, ValueError):
                            pass
                    elif msg.get("bytes"):
                        if not proc.isalive():
                            break
                        proc.write(msg["bytes"])
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

        if init_cmd:
            async def _inject_init_cmd():
                await asyncio.sleep(0.6)
                if proc.isalive():
                    proc.write((init_cmd + "\r").encode())
            asyncio.create_task(_inject_init_cmd())

        try:
            read_task = asyncio.create_task(read_pty())
            write_task = asyncio.create_task(write_pty())
            done, pending = await asyncio.wait(
                [read_task, write_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
        finally:
            if proc.isalive():
                proc.terminate()
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception:
                    pass


def _read_pty_data(proc) -> bytes | None:
    """Blocking read from pty. Returns None on EOF."""
    try:
        return proc.read(4096)
    except EOFError:
        return None
    except Exception:
        return None
