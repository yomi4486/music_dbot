import json,os
if not os.path.exists('./playlist/editlist.json'):
    with open('./editlist.json', 'w',encoding="utf-8") as file:
        file.write(json.dumps({}, indent=4,ensure_ascii = False))

if not os.path.exists('./cache.json.json'):
    with open('./cache.json.json', 'w',encoding="utf-8") as file:
        file.write(json.dumps({}, indent=4,ensure_ascii = False))