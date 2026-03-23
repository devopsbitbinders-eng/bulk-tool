from utils import get_now_utc
import datetime
print(f"GET_NOW_UTC: {get_now_utc()}")
print(f"DATETIME.NOW(UTC): {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print(f"DATETIME.NOW(): {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
