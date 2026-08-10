import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

READER_BASE_URL = os.getenv("READER_BASE_URL", "http://10.0.0.112:8080")
READER_START_URL = os.getenv("READER_START_URL", "/InventoryController/startInventoryRequest")
READER_STOP_URL = os.getenv("READER_STOP_URL", "/InventoryController/stopInventoryRequest")
READER_POLL_URL = os.getenv("READER_POLL_URL", "/InventoryController/tagReportingDataAndIndex")
READER_SINGLE_URL = os.getenv("READER_SINGLE_URL", "/ReadController/tagReadRequest")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", 0.1))

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))