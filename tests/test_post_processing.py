from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

import pytest

from spkup.config import AppConfig
from spkup.post_processing import (
    KEYRING_SERVICE,
    KEYRING_USERNAME,
    apply_replacements,
    build_system_prompt,
    post_process,
)


# ---------------------------------------------------------------------------
# Replacements
# ---------------------------------------------------------------------------


def test_replacements_are_case_insensitive() -> None:
    assert apply_replacements("Temple Base rocks", {"temple base": "Tempobase"}) == (
        "Tempobase rocks"
    )


def test_replacements_respect_word_boundaries() -> None:
    assert apply_replacements("speak up, speaker", {"speak up": "spkup", "speak": "X"}) == (
        "spkup, speaker"
    )


def test_replacements_handle_keys_with_symbols_and_backslashes_in_target() -> None:
    assert apply_replacements("use c++ now", {"c++": r"C\+\+"}) == r"use C\+\+ now"


def test_empty_replacements_return_text_unchanged() -> None:
    assert apply_replacements("hello", {}) == "hello"


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def test_system_prompt_includes_vocabulary_instructions_and_guards() -> None:
    prompt = build_system_prompt(["Tempobase", "spkup"], "Use formal tone.")

    assert "Tempobase" in prompt and "spkup" in prompt
    assert "Use formal tone." in prompt
    assert "never translate" in prompt.lower()
    assert "never answer" in prompt.lower()


def test_system_prompt_omits_empty_sections() -> None:
    prompt = build_system_prompt([], "")

    assert "Vocabulary" not in prompt
    assert "User instructions" not in prompt


# ---------------------------------------------------------------------------
# HTTP client against a local fake server
# ---------------------------------------------------------------------------


class _FakeServer:
    def __init__(self, status: int = 200, body: bytes = b"", delay: float = 0) -> None:
        self.requests: list[tuple[dict, dict]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers["Content-Length"])
                outer.requests.append(
                    (dict(self.headers), json.loads(self.rfile.read(length)))
                )
                if delay:
                    threading.Event().wait(delay)
                self.send_response(status)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args) -> None:
                pass

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self._server.server_port}/v1"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def _reply(content) -> bytes:
    return json.dumps({"choices": [{"message": {"content": content}}]}).encode()


@pytest.fixture
def server_factory():
    servers: list[_FakeServer] = []

    def make(**kwargs) -> _FakeServer:
        server = _FakeServer(**kwargs)
        servers.append(server)
        return server

    yield make
    for server in servers:
        server.close()


def _config(base_url: str, **overrides) -> AppConfig:
    return AppConfig(
        post_processing_enabled=True,
        post_processing_base_url=base_url,
        post_processing_model="tiny-llm",
        vocabulary=["Tempobase"],
        post_processing_instructions="Keep it short.",
        **overrides,
    )


def test_local_success_sends_openai_compatible_request_without_auth(server_factory) -> None:
    server = server_factory(body=_reply("  Tempobase works.  "))

    with patch("spkup.post_processing.keyring") as kr:
        result = post_process("temple base works", _config(server.base_url))

    assert result == "Tempobase works."
    kr.get_password.assert_not_called()
    headers, body = server.requests[0]
    assert "Authorization" not in headers
    assert body["model"] == "tiny-llm"
    assert body["temperature"] == 0
    assert body["messages"][0]["role"] == "system"
    assert "Tempobase" in body["messages"][0]["content"]
    assert "Keep it short." in body["messages"][0]["content"]
    assert "temple base works" in body["messages"][1]["content"]


def test_openai_provider_sends_bearer_key_from_keyring(server_factory) -> None:
    server = server_factory(body=_reply("ok"))

    with patch("spkup.post_processing.keyring") as kr:
        kr.get_password.return_value = "sk-secret"
        result = post_process("raw", _config(server.base_url, post_processing_provider="openai"))

    assert result == "ok"
    kr.get_password.assert_called_once_with(KEYRING_SERVICE, KEYRING_USERNAME)
    assert server.requests[0][0]["Authorization"] == "Bearer sk-secret"


def test_think_block_is_stripped(server_factory) -> None:
    server = server_factory(body=_reply("<think>\nhmm\n</think>\n\nClean text."))

    assert post_process("raw", _config(server.base_url)) == "Clean text."


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": 500, "body": b"boom"},
        {"body": b"not json"},
        {"body": _reply("   ")},
        {"body": _reply("<think>only thinking</think>")},
        {"body": json.dumps({"choices": []}).encode()},
    ],
    ids=["http-error", "bad-json", "empty-reply", "only-think", "no-choices"],
)
def test_failures_fall_back_to_raw_text_and_warn(server_factory, caplog, kwargs) -> None:
    server = server_factory(**kwargs)

    with caplog.at_level("WARNING", logger="spkup.post_processing"):
        assert post_process("raw text", _config(server.base_url)) == "raw text"

    assert "local" in caplog.text and "tiny-llm" in caplog.text


def test_connection_error_falls_back_to_raw_text() -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    assert post_process("raw", _config(f"http://127.0.0.1:{port}/v1")) == "raw"


def test_timeout_falls_back_to_raw_text(server_factory, monkeypatch) -> None:
    monkeypatch.setattr("spkup.post_processing.TIMEOUT_SECONDS", 0.2)
    server = server_factory(body=_reply("late"), delay=1)

    assert post_process("raw", _config(server.base_url)) == "raw"


def test_openai_without_key_falls_back_without_request(server_factory) -> None:
    server = server_factory(body=_reply("never"))

    with patch("spkup.post_processing.keyring") as kr:
        kr.get_password.return_value = None
        result = post_process("raw", _config(server.base_url, post_processing_provider="openai"))

    assert result == "raw"
    assert server.requests == []


def test_keyring_exception_falls_back_to_raw_text(caplog) -> None:
    with patch("spkup.post_processing.keyring") as kr:
        kr.get_password.side_effect = RuntimeError("keychain locked")
        with caplog.at_level("WARNING", logger="spkup.post_processing"):
            result = post_process(
                "raw", _config("http://127.0.0.1:9/v1", post_processing_provider="openai")
            )

    assert result == "raw"
    assert "keychain locked" in caplog.text


def test_api_key_never_logged(server_factory, caplog) -> None:
    server = server_factory(status=401, body=b"bad key")

    with patch("spkup.post_processing.keyring") as kr:
        kr.get_password.return_value = "sk-secret"
        with caplog.at_level("DEBUG"):
            post_process("raw", _config(server.base_url, post_processing_provider="openai"))

    assert "sk-secret" not in caplog.text


def test_success_logs_provider_model_and_latency(server_factory, caplog) -> None:
    server = server_factory(body=_reply("ok"))

    with caplog.at_level("INFO", logger="spkup.post_processing"):
        post_process("raw", _config(server.base_url))

    assert "provider=local" in caplog.text
    assert "model=tiny-llm" in caplog.text


def test_reasoning_effort_sent_when_set_and_omitted_for_model_default(server_factory) -> None:
    server = server_factory(body=_reply("ok"))

    post_process("raw", _config(server.base_url))
    post_process("raw", _config(server.base_url, post_processing_reasoning_effort=""))

    assert server.requests[0][1]["reasoning_effort"] == "none"
    assert "reasoning_effort" not in server.requests[1][1]


def test_on_error_gets_server_error_message(server_factory) -> None:
    body = json.dumps({"error": {"message": "Unsupported parameter: 'reasoning_effort'"}})
    server = server_factory(status=400, body=body.encode())
    reasons: list[str] = []

    result = post_process("raw", _config(server.base_url), reasons.append)

    assert result == "raw"
    assert reasons == ["HTTP 400: Unsupported parameter: 'reasoning_effort'"]


def test_on_error_not_called_on_success(server_factory) -> None:
    server = server_factory(body=_reply("ok"))
    reasons: list[str] = []

    assert post_process("raw", _config(server.base_url), reasons.append) == "ok"
    assert reasons == []
