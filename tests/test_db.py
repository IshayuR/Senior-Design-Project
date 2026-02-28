from dotenv import load_dotenv
load_dotenv()
from app.database.mongo import get_mongo_db

db = get_mongo_db()
device = db.Devices.find_one({'legacyId': 1})

if device:
    print(f'Light state: {device.get("lightState")}')
    print(f'Brightness: {device.get("brightness")}')
    
    # Check history
    history = db.light_history.find_one({'legacyId': 1}, sort=[('timestamp', -1)])
    if history:
        print(f'Last action: {history.get("action")} at {history.get("timestamp")}')
    else:
        print("No history found")
else:
    print("No device found with legacyId 1")
