import pytest
import requests

from app.services.llm_service import (
    LLMService,
    OllamaRequestError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)


class FakeResponse:
    def __init__(
        self,
        *,
        data: dict | None = None,
        error: Exception | None = None,
    ):
        self.data = data or {}
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self) -> dict:
        return self.data


def test_generate_returns_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            data={"response": "  hello  "}
        ),
    )

    service = LLMService(
        "http://localhost:11434",
        "qwen2.5:7b",
    )

    assert service.generate("prompt") == "hello"


def test_generate_maps_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("slow")

    monkeypatch.setattr(
        requests,
        "post",
        raise_timeout,
    )

    service = LLMService(
        "http://localhost:11434",
        "qwen2.5:7b",
    )

    with pytest.raises(OllamaTimeoutError):
        service.generate("prompt")


def test_generate_maps_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(
        requests,
        "post",
        raise_connection_error,
    )

    service = LLMService(
        "http://localhost:11434",
        "qwen2.5:7b",
    )

    with pytest.raises(OllamaUnavailableError):
        service.generate("prompt")


def test_generate_maps_other_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            error=requests.HTTPError(
                "bad upstream response"
            )
        ),
    )

    service = LLMService(
        "http://localhost:11434",
        "qwen2.5:7b",
    )

    with pytest.raises(OllamaRequestError):
        service.generate("prompt")
