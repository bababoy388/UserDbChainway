from fastapi import FastAPI
from app import endpoints

app = FastAPI(title="API Reader")
app.include_router(endpoints.router)

@app.get("/")
async def root():
    return {"message": "API Reader is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", port=8001, reload=True)
