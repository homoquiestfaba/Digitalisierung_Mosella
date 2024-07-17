import json

f = open("JSON/ausonius-decimus-magnus__mosella__latin.json", "r", encoding="utf-8")

data = json.load(f)

mosella = data["text"]["0"]
[print(mosella[verse]) for verse in mosella]