import pytest
import httpx
import respx

from core.embeddings import embed_text


@pytest.mark.asyncio
async def test_embed_text_returns_1536_floats():
    mock_vec = [0.1] * 1536
    with respx.mock:
        respx.post("https://api.openai.com/v1/embeddings").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [{"embedding": mock_vec, "index": 0}],
                    "model": "text-embedding-3-small",
                    "usage": {"prompt_tokens": 2, "total_tokens": 2},
                },
            )
        )
        result = await embed_text("hello world")

    assert isinstance(result, list)
    assert len(result) == 1536
    assert all(isinstance(v, float) for v in result)


@pytest.mark.asyncio
async def test_embed_text_sends_correct_model():
    mock_vec = [0.5] * 1536
    with respx.mock:
        route = respx.post("https://api.openai.com/v1/embeddings").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [{"embedding": mock_vec, "index": 0}],
                    "model": "text-embedding-3-small",
                    "usage": {"prompt_tokens": 3, "total_tokens": 3},
                },
            )
        )
        await embed_text("test input")

    assert route.called
    request_body = route.calls[0].request
    import json
    body = json.loads(request_body.content)
    assert body["model"] == "text-embedding-3-small"
    assert body["input"] == "test input"
