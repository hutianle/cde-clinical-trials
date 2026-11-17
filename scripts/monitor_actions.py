import urllib.request
import json

url = 'https://api.github.com/repos/hutianle/cde-clinical-trials/actions/runs?per_page=5'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        runs = data.get('workflow_runs', [])
        for r in runs:
            print(f"ID: {r['id']} | Event: {r['event']} | Status: {r['status']} | Conclusion: {r['conclusion']} | SHA: {r['head_sha'][:7]} | Title: {r.get('display_title')}")
        
        if runs and runs[0]['status'] == 'in_progress':
            latest = runs[0]
            jobs_req = urllib.request.Request(latest['jobs_url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(jobs_req) as jresp:
                jdata = json.loads(jresp.read().decode('utf-8'))
                for j in jdata.get('jobs', []):
                    print(f"\nActive Job: {j['name']} [{j['status']}]")
                    for s in j.get('steps', []):
                        print(f"  - {s['name']}: {s['status']} ({s['conclusion']})")
except Exception as e:
    print('Error:', e)
