import json, pathlib, sys, time
r=pathlib.Path(__file__).resolve().parents[1]
if len(sys.argv)==2 and sys.argv[1]=='targets': print(json.dumps(json.loads((r/'deploy/targets.json').read_text()),indent=2))
elif len(sys.argv)==4 and sys.argv[1]=='deploy':
    with (r/'deploy/action-log.jsonl').open('a') as f: f.write(json.dumps({'at':time.time(),'service':sys.argv[2],'target':sys.argv[3]})+'\n')
    print('Local deployment request recorded; no network action performed.')
else: raise SystemExit('usage: deployctl.py targets | deploy SERVICE TARGET')
