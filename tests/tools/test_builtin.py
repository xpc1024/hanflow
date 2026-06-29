import pytest

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.code_exec import CodeExecServer
from hanflow.tools.builtin.filesystem import FilesystemServer
from hanflow.tools.builtin.http_request import HTTPRequestServer
from hanflow.tools.builtin.shell import ShellServer
from hanflow.tools.builtin.web_fetch import WebFetchServer
from hanflow.tools.builtin.web_search import WebSearchServer


@pytest.mark.asyncio
async def test_filesystem_read_write(tmp_path):
    srv = FilesystemServer(root=tmp_path)
    await srv.call("write", {"path": "a.txt", "content": "hi"})
    out = await srv.call("read", {"path": "a.txt"})
    assert out == "hi"


@pytest.mark.asyncio
async def test_filesystem_rejects_escape(tmp_path):
    (tmp_path.parent / "secret.txt").write_text("secret")
    srv = FilesystemServer(root=tmp_path)
    with pytest.raises(HanflowError):
        await srv.call("read", {"path": "../secret.txt"})


@pytest.mark.asyncio
async def test_shell_runs_command(tmp_path):
    srv = ShellServer(workspace=tmp_path, enabled=True)
    out = await srv.call("run", {"cmd": "echo hello"})
    assert "hello" in out["stdout"]


@pytest.mark.asyncio
async def test_shell_disabled_by_default(tmp_path):
    srv = ShellServer(workspace=tmp_path, enabled=False)
    with pytest.raises(HanflowError):
        await srv.call("run", {"cmd": "echo hi"})


@pytest.mark.asyncio
async def test_web_fetch_returns_markdown(monkeypatch):
    srv = WebFetchServer()

    async def fake_fetch(url, **kw):
        return "# Title\nbody"

    monkeypatch.setattr(srv, "_fetch", fake_fetch)
    out = await srv.call("fetch", {"url": "https://example.com"})
    assert "Title" in out["markdown"]


@pytest.mark.asyncio
async def test_http_request_posts(httpx_mock):
    httpx_mock.add_response(url="https://x/api", method="POST", json={"ok": True})
    srv = HTTPRequestServer()
    out = await srv.call("request", {"url": "https://x/api", "method": "POST", "json": {"a": 1}})
    assert out["status"] == 200


@pytest.mark.asyncio
async def test_code_exec_python(tmp_path):
    srv = CodeExecServer(workspace=tmp_path, mode="none")
    out = await srv.call("run", {"language": "python", "code": "print(1+1)"})
    assert "2" in out["stdout"]


@pytest.mark.asyncio
async def test_web_search_returns_empty_by_default():
    srv = WebSearchServer()
    out = await srv.call("search", {"query": "anything"})
    assert out == []


@pytest.mark.asyncio
async def test_vector_search_not_configured_raises():
    from hanflow.tools.builtin.vector_search import VectorSearchServer

    srv = VectorSearchServer()
    with pytest.raises(HanflowError):
        await srv.call("search", {"store": "kb", "query": "x"})


def test_each_builtin_lists_tools():
    for srv in [
        FilesystemServer(root="."),
        ShellServer(workspace=".", enabled=True),
        WebSearchServer(),
        WebFetchServer(),
        CodeExecServer(workspace=".", mode="none"),
        HTTPRequestServer(),
    ]:
        assert srv.tools(), f"{srv.name} lists no tools"
        for t in srv.tools():
            assert t.input_schema  # every tool has a schema
