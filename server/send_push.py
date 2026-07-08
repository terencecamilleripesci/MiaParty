#!/usr/bin/env python3
"""Send the birthday-eve push to every subscriber. Run by mia-push.timer on 11 Aug."""
import json, os, sys
from pywebpush import webpush, WebPushException

BASE = os.path.dirname(os.path.abspath(__file__))
SUBS = os.path.join(BASE, 'subs.jsonl')
MSG = json.dumps({
    "title": "Mia turns 1 tomorrow! 🎂",
    "body": "Tomorrow is Mia's big day — you're her photographer! Your 50 shots unlock at the party 📸🎀",
    "url": "https://terencecamilleripesci.github.io/MiaParty/"
})
if not os.path.exists(SUBS):
    print("no subscribers"); sys.exit(0)
sent = failed = 0
seen = set()
for line in open(SUBS):
    line = line.strip()
    if not line:
        continue
    sub = json.loads(line)
    ep = sub.get('endpoint')
    if not ep or ep in seen:
        continue
    seen.add(ep)
    try:
        webpush(sub, MSG,
                vapid_private_key=os.path.join(BASE, 'keys', 'private_key.pem'),
                vapid_claims={"sub": "mailto:terencecamilleripesci@gmail.com"})
        sent += 1
    except Exception:
        failed += 1          # one bad subscription must never break the broadcast
print(f"push done: sent={sent} failed={failed}")
