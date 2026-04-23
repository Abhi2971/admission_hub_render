import os
from dotenv import load_dotenv

load_dotenv()
print("MONGO_URI:", os.getenv("MONGO_URI"))
print("MONGO_DB_NAME:", os.getenv("MONGO_DB_NAME"))