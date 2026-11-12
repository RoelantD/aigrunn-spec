"""REST + SSE API (T042, T070, T081): real uvicorn server on an ephemeral port, fake externals."""

import asyncio
import json
import socket
import time

import httpx
import pytest
import uvicorn

from app.main import create_app
from tests.conftest import TEST_SESSION
from tests.fixtures.fakes import EX_DAY1_P1, EX_DAY1_P2, proposal


def _port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture
async def server(make_env):
    env = await make_env([proposal("drift", EX_DAY1_P1), proposal("products", EX_DAY1_P2)])
    port = _port()
    app = create_app(services=env.svc)
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"))
    task = asyncio.create_task(srv.serve())
    for _ in range(200):
        if srv.started:
            break
        await asyncio.sleep(0.02)
    base = f"http://127.0.0.1:{port}/api"
    async with httpx.AsyncClient(base_url=base, timeout=20) as client:
        yield env, client, base
    srv.should_exit = True
    await task


async def _read_sse(base: str, path: str, headers: dict, until_type: str, sink: list, timeout=20):
    async with httpx.AsyncClient(timeout=timeout) as c:
        async with c.stream("GET", base + path, headers=headers) as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    ev = json.loads(line[6:])
                    ev["_received"] = time.monotonic()
                    sink.append(ev)
                    if ev["type"] == until_type:
                        return


async def test_create_requires_authorization(server):
    env, client, _ = server
    r = await client.post("/runs", json={"calendar_url": "https://adventofcode.com/2024", "day_from": 1,
                                         "day_to": 1, "auto_submit": True})
    assert r.status_code == 422 and "authorization" in r.text
    r = await client.post("/runs", json={"calendar_url": "https://evil.example/2024", "authorize_submission": True})
    assert r.status_code == 422


async def test_full_run_over_http_with_sse_and_resume(server):
    env, client, base = server
    r = await client.post("/runs", json={"calendar_url": "https://adventofcode.com/2024", "day_from": 1,
                                         "day_to": 1, "auto_submit": True, "authorize_submission": True,
                                         "config": {"aoc_min_interval_s": 1}})
    assert r.status_code == 201, r.text
    run_id = r.json()["id"]
    events: list = []
    reader = asyncio.create_task(_read_sse(base, f"/runs/{run_id}/events/stream", {}, "run.completed", events))
    await asyncio.sleep(0.2)
    t_start = time.monotonic()
    assert (await client.post(f"/runs/{run_id}/start")).status_code == 200
    assert (await client.post(f"/runs/{run_id}/start")).status_code == 409  # already active
    await asyncio.wait_for(reader, 20)
    ids = [e["id"] for e in events]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert any(e["type"] == "star.earned" for e in events)
    # SC-004: events are delivered promptly (whole run with fakes is far below 2 s per event)
    assert events[-1]["_received"] - t_start < 10

    # Resume from the middle with Last-Event-ID: only later events, no duplicates.
    mid = ids[len(ids) // 2]
    resumed: list = []
    await _read_sse(base, f"/runs/{run_id}/events/stream", {"Last-Event-ID": str(mid)}, "run.completed", resumed)
    assert [e["id"] for e in resumed] == [i for i in ids if i > mid]

    prog = (await client.get(f"/runs/{run_id}/progress")).json()
    day1 = prog["days"][0]["parts"]
    assert day1["1"]["ui_state"] == "verified" and day1["2"]["ui_state"] == "verified"
    assert prog["stars"]["earned_this_run"] == 2
    revs = (await client.get(f"/runs/{run_id}/parts/1/1/revisions")).json()
    assert revs[0]["code"].startswith("# BEHAVIOR: drift") and revs[0]["results"]
    m = (await client.get(f"/runs/{run_id}/metrics")).json()
    assert m["by_model"]["workhorse"]["calls"] == 2
    subs = (await client.get(f"/runs/{run_id}/submissions")).json()
    assert [s["outcome"] for s in subs] == ["CORRECT", "CORRECT"]

    # Replay over HTTP
    rep = (await client.post(f"/runs/{run_id}/replay", json={"speed": 100})).json()
    rep_events: list = []
    await _read_sse(base, f"/runs/{rep['id']}/events/stream", {}, "run.completed", rep_events)
    assert all(e["replay"] for e in rep_events)

    d = await client.delete(f"/runs/{rep['id']}")
    assert "not affected" in d.json()["notice"]

    # SC-009: no secret appears in any API payload or event.
    blobs = [json.dumps(events), json.dumps(prog), json.dumps(revs), json.dumps(m), json.dumps(subs),
             (await client.get("/config")).text, (await client.get("/runs")).text]
    for b in blobs:
        assert TEST_SESSION not in b


async def test_connections_verify_never_submits(server):
    env, client, _ = server
    r = (await client.post("/connections/verify", json={"checks": ["storage", "aoc", "workhorse", "sandbox"]})).json()
    by = {c["name"]: c for c in r["checks"]}
    assert by["storage"]["status"] == "pass" and by["aoc"]["status"] == "pass"
    assert by["workhorse"]["status"] == "pass" and by["sandbox"]["status"] == "pass"
    assert env.site.posts == []
    assert not any(p.endswith("/input") for _, p in env.site.requests)


async def test_connections_verify_invalid_session(server):
    env, client, _ = server
    env.site.logged_in = False
    r = (await client.post("/connections/verify", json={"checks": ["aoc", "storage"]})).json()
    by = {c["name"]: c for c in r["checks"]}
    assert by["aoc"]["status"] == "fail" and by["storage"]["status"] == "pass" and r["overall"] == "fail"
    assert env.site.posts == []


async def test_logs_do_not_contain_secrets(server, capsys):
    env, client, _ = server
    from app.logsetup import get_logger

    get_logger("t").info("probe", cookie=f"session={TEST_SESSION}", text=f"value {TEST_SESSION}")
    out = capsys.readouterr()
    assert TEST_SESSION not in out.out + out.err
