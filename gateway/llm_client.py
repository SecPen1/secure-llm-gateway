from .schemas import Message, Role


class LLMClient:
    def generate(self, messages: list[Message]) -> str:
        raise NotImplementedError


class StubLLMClient(LLMClient):
    """Deterministic, no network call — the default, so the repo runs with
    zero external dependencies or API keys. This is plumbing for slice 4
    (output filtering needs a response to filter); it is not a real upstream
    integration. See README Slice 4 for why that's a deliberate v1 scope cut,
    not an oversight.
    """

    def generate(self, messages: list[Message]) -> str:
        last_user_message = next(
            (message for message in reversed(messages) if message.role == Role.user),
            None,
        )
        content = last_user_message.content if last_user_message else ""
        return f"(stub response, no upstream LLM configured) You said: {content}"


def get_llm_client() -> LLMClient:
    return StubLLMClient()
