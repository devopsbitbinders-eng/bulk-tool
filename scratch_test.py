import json
with open("last_uploaded.csv", "rb") as f:
    data = json.load(f)
print("Total records in last uploaded:", len(data))
