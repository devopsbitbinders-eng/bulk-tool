import sys
lines = open('c:/Users/kajal/Downloads/messanger/main.py', encoding='utf-8').readlines()
for i, l in enumerate(lines):
    if 'error_msg = status_update.get("errors", [{}])[0].get("message", "Unknown Error")' in l or 'error_msg' in l:
        if i > 1000 and i < 1100:
            print("FOUND AT", i)
            print("".join(lines[i-15:i+30]))
            break
