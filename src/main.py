import uvicorn
from fastapi import FastAPI
import httpx

app = FastAPI(
    title="Steam reg test",
)

@app.get("/")
async def hello():

    url = "http://localhost:8000/api/auth/steam/auth_data"
    payload = {
        "user_ip": "1.1.1.1",
        "steam_id": "123123123123",
        "username": "я мамонт",
        "domain_id": 2
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(response.json())

    return response.status_code

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, port=9000)