"""WebSocket → pty terminal bridge using ptyprocess."""
from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from fastapi.websockets import WebSocket, WebSocketDisconnect, WebSocketState


class TerminalManager:
    """Manages WebSocket ↔ pty sessions."""

    async def handle(self, websocket: WebSocket) -> None:
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

        # Get working directory from query params if available
        cwd = str(Path.cwd())

        try:
            proc = ptyprocess.PtyProcess.spawn(
                [shell],
                cwd=cwd,
                env={
                    **os.environ,
                    "TERM": "xterm-256color",
                    "COLUMNS": "220",
                    "LINES": "50",
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
            """Receive from WebSocket and write to pty."""
            while True:
                try:
                    data = await websocket.receive_bytes()
                    if not proc.isalive():
                        break
                    proc.write(data)
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

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
