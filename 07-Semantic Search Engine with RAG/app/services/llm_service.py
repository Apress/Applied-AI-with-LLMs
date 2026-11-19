import requests


class OllamaUnavailableError(Exception):
    pass


class OllamaTimeoutError(Exception):
    pass


class OllamaRequestError(Exception):
    pass


class LLMService:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        except requests.Timeout as exc:
            raise OllamaTimeoutError(
                f"Ollama did not respond within {self.timeout:g} seconds. "
                "The model may still be loading or generation may be too slow."
            ) from exc

        except requests.ConnectionError as exc:
            raise OllamaUnavailableError(
                "Ollama is unavailable. Semantic search still works, "
                "but the local LLM cannot be reached."
            ) from exc

        except requests.RequestException as exc:
            raise OllamaRequestError(
                "The request to Ollama failed."
            ) from exc

        return str(data.get("response", "")).strip()
