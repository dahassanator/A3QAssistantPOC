from unittest.mock import MagicMock

from assistant.orchestrator import AssistantAnswer, handle_question


def test_handle_question_calls_claude_and_returns_text():
    fake_text_block = MagicMock(type="text", text="You're all set.")
    fake_response = MagicMock(content=[fake_text_block])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    result = handle_question(
        "What's a canvassing contact?",
        {"state": "Alabama", "office": "Mayoral"},
        client=fake_client,
    )

    assert isinstance(result, AssistantAnswer)
    assert result.text == "You're all set."

    _, kwargs = fake_client.messages.create.call_args
    assert kwargs["model"] == "claude-haiku-4-5"
    assert "Alabama" in kwargs["system"]
    assert kwargs["messages"] == [
        {"role": "user", "content": "What's a canvassing contact?"}
    ]
