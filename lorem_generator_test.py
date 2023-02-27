import pytest
from httpx import AsyncClient

from lorem_generator import app


@pytest.mark.anyio
async def test_lorem():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/lorem", json={"paragraphs": 2,  "words": 10})
    assert response.status_code == 200
    assert len(response.json()["paragraphs"]) == 2
    assert len(response.json()["paragraphs"][0].split(' ')) == 10
