import uvicorn
from fastapi import FastAPI
from auth.router import router as auth_router
from inventory.router import router as inventory_router

app = FastAPI(
    title="CSMONEY BACKEND",
)

app.include_router(auth_router)
app.include_router(inventory_router)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, port=9000)