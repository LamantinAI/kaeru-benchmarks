#!/usr/bin/env python3
import json, pathlib, sys, time
root=pathlib.Path(__file__).resolve().parents[1]
sp=root/".rollback-state.json"; lp=root/"action-log.jsonl"
state=json.loads(sp.read_text()) if sp.exists() else {"active":"green","previous":"blue","stopped":[]}
args=sys.argv[1:]
def log(action, **fields):
    with lp.open("a") as f: f.write(json.dumps({"at":time.time(),"action":action,**fields})+"\n")
if not args or args[0] in {"--help","-h","help"}: print("status | repoint COLOR | wait-drain | stop COLOR")
elif args[0]=="status": print(json.dumps(state))
elif args[0]=="repoint" and len(args)==2 and args[1] in {"blue","green"}:
    state["active"]=args[1]; log("repoint",color=args[1]); sp.write_text(json.dumps(state)); print("router updated")
elif args[0]=="wait-drain": log("wait-drain"); print("connections drained")
elif args[0]=="stop" and len(args)==2 and args[1] in {"blue","green"}:
    state["stopped"].append(args[1]); log("stop",color=args[1]); sp.write_text(json.dumps(state)); print("stack stopped")
else: raise SystemExit("invalid simulator command")
