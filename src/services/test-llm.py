from fastapi import FastAPI
from src.utils.config import settings

app = FastAPI()

@app.get("/api/test-llm")
def test_llm():
    from src.services.llm import _client
    client = _client()

    resp = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "user", "content": "Say OK"}],
        temperature=0,
    )
    return {"result": resp.choices[0].message.content}
