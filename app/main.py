from fastapi import FastAPI
from app import endpoints

app = FastAPI(title="RFID Reader Gateway")
app.include_router(endpoints.router)

@app.get("/")
async def root():
    return {"message": "RFID Reader Gateway is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
