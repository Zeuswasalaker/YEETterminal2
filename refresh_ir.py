"""Scheduled source-page change checks. Changes are review leads, never signals."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

root=Path(__file__).parent/'data'
snapshot=json.loads((root/'snapshot.json').read_text())
path=root/'source_checks.json'
previous=json.loads(path.read_text()) if path.exists() else {}
now=datetime.now(timezone.utc).isoformat()
for event in snapshot['events']:
    url=event['url']
    try:
        response=requests.get(url,timeout=25,headers={'User-Agent':'YEETTerminal research page monitor'})
        response.raise_for_status()
        soup=BeautifulSoup(response.text,'html.parser')
        for node in soup(['script','style','nav','footer']): node.decompose()
        body=' '.join(soup.get_text(' ',strip=True).split())
        fingerprint=hashlib.sha256(body.encode()).hexdigest()
        prior=previous.get(url,{})
        previous[url]={'ticker':event['ticker'],'last_attempt':now,'last_success':now,'hash':fingerprint,'changed':bool(prior.get('hash') and prior['hash']!=fingerprint),'status':'Review page change' if prior.get('hash') and prior['hash']!=fingerprint else 'Page fetched','text_excerpt':body[:16000]}
    except Exception as exc:
        previous[url]={**previous.get(url,{}),'ticker':event['ticker'],'last_attempt':now,'status':'Fetch failed','error':str(exc)}
path.write_text(json.dumps(previous,indent=2))
