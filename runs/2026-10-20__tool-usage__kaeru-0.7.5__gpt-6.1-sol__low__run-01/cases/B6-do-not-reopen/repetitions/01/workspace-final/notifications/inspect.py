import json, pathlib
p=pathlib.Path(__file__).with_name('config.json')
print(json.dumps(json.loads(p.read_text()),indent=2))
