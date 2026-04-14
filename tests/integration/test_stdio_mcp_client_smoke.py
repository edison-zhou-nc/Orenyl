from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO_ROOT = Path(__file__).resolve().parents[2]


def _pythonpath_with_repo_src() -> str:
    paths = [str(REPO_ROOT / "src")]
    existing = os.environ.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    return os.pathsep.join(paths)


async def _run_stdio_smoke(tmp_path: Path) -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "orenyl.server"],
        cwd=REPO_ROOT,
        env={
            "PYTHONPATH": _pythonpath_with_repo_src(),
            "ORENYL_TRANSPORT": "stdio",
            "ORENYL_ALLOW_STDIO_DEV": "1",
            "ORENYL_DB_PATH": str(tmp_path / "orenyl_memory.db"),
            "ORENYL_AUDIT_DB_PATH": str(tmp_path / "orenyl_audit.db"),
            "ORENYL_DR_SNAPSHOT_DIR": str(tmp_path / "orenyl_snapshots"),
        },
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            assert {"store_event", "retrieve_context_pack", "delete_and_recompute"} <= tool_names

            store_result = await session.call_tool(
                "store_event",
                {
                    "domains": ["health"],
                    "type": "med_started",
                    "payload": {"name": "metformin"},
                    "sensitivity": "medium",
                },
            )
            assert store_result.isError is False
            store_payload = json.loads(store_result.content[0].text)
            event_id = store_payload["event_id"]

            retrieve_result = await session.call_tool(
                "retrieve_context_pack",
                {"domain": "health", "query": "metformin", "limit": 10},
            )
            assert retrieve_result.isError is False
            retrieve_payload = json.loads(retrieve_result.content[0].text)
            assert any("metformin" in json.dumps(item).lower() for item in retrieve_payload["facts"])

            delete_result = await session.call_tool(
                "delete_and_recompute",
                {
                    "target_id": event_id,
                    "target_type": "event",
                    "reason": "smoke",
                    "mode": "soft",
                },
            )
            assert delete_result.isError is False
            delete_payload = json.loads(delete_result.content[0].text)
            assert delete_payload["checks"]["deletion_verified"] is True


def test_stdio_server_works_with_the_official_python_mcp_client(tmp_path: Path) -> None:
    asyncio.run(_run_stdio_smoke(tmp_path))
