#!/usr/bin/env python3
import argparse, time, requests, re, subprocess
from collections import Counter

MAX_LIMIT = 4500
IP_JSON_RE = re.compile(r'"client_ip":"(\d{1,3}(?:\.\d{1,3}){3})"')

def send_discord_message(webhook_url, message):
    """Send a Discord notification through the configured webhook."""
    if not webhook_url:
        return
    try:
        payload = {"content": message}
        r = requests.post(webhook_url, json=payload, timeout=10)
        if r.status_code >= 300:
            print(f"⚠️ Discord webhook error {r.status_code}: {r.text}")
    except Exception as e:
        print("⚠️ Discord notification failed:", e)

def epoch_nanos(ts=None):
    return int((ts or time.time()) * 1e9)

def query_loki(loki_url, loki_ns, start_ns, end_ns, host_filter, limit=MAX_LIMIT):
    # Only include logs for the requested host.
    q = '{namespace="%s"} |= "client_ip" |= "%s"' % (loki_ns, host_filter)
    params = {
        "query": q,
        "start": str(start_ns),
        "end": str(end_ns),
        "limit": str(limit),
        "direction": "BACKWARD"
    }
    url = loki_url.rstrip("/") + "/loki/api/v1/query_range"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

def extract_ips_from_streams(loki_json):
    cnt = Counter()
    for stream in loki_json.get("data", {}).get("result", []):
        for _, line in stream.get("values", []):
            for ip in IP_JSON_RE.findall(line):
                cnt[ip] += 1
    return cnt

def build_policy_yaml(ip, selector_namespace):
    name = "block-" + ip.replace(".", "-")
    return f"""apiVersion: crd.projectcalico.org/v1
kind: GlobalNetworkPolicy
metadata:
  name: {name}
spec:
  selector: projectcalico.org/namespace == "{selector_namespace}"
  types:
    - Ingress
  ingress:
    - action: Deny
      source:
        nets:
          - {ip}/32
    - action: Allow
"""

def apply_policy(yaml_text):
    p = subprocess.run(["kubectl", "apply", "-f", "-"],
                       input=yaml_text.encode("utf-8"),
                       capture_output=True,
                       timeout=15)
    return p.returncode, p.stdout.decode(), p.stderr.decode()

def main():
    ap = argparse.ArgumentParser(description="DDoS detector based on Loki logs and Calico blocklists")
    ap.add_argument("--loki-url", default="http://localhost:3100", help="Loki server URL")
    ap.add_argument("--loki-namespace", default="ingress-nginx", help="Namespace where the ingress controller runs")
    ap.add_argument("--duration", type=int, default=120, help="Analysis window in seconds")
    ap.add_argument("--threshold", type=int, default=50, help="Minimum requests per IP before it is considered suspicious")
    ap.add_argument("--selector-namespace", default="ingress-nginx", help="Namespace selector for the Calico policy")
    ap.add_argument("--filter-host", default="cosmin-employee-leave.bench.az.am-isd.com", help="Host to filter in Loki logs")
    ap.add_argument("--apply", action="store_true", help="Apply the Calico policy automatically")
    ap.add_argument("--discord-webhook", default=None, help="Discord webhook used for notifications")
    ap.add_argument("--dry-run", action="store_true", help="Simulation mode without applying changes")
    ap.add_argument("--top", type=int, default=5, help="Maximum number of IPs displayed in the top list")
    args = ap.parse_args()

    start_ns, end_ns = epoch_nanos(time.time() - args.duration), epoch_nanos()
    print(f"🔍 Querying Loki {args.loki_url}")
    print(f"   Namespace = {args.loki_namespace}")
    print(f"   Host filter = {args.filter_host}")
    print(f"   Window = {args.duration}s")

    try:
        j = query_loki(args.loki_url, args.loki_namespace, start_ns, end_ns, args.filter_host)
    except Exception as e:
        msg = f"❌ Failed to query Loki: {e}"
        print(msg)
        send_discord_message(args.discord_webhook, msg)
        return 2

    counts = extract_ips_from_streams(j)
    if not counts:
        print("✅ No IPs detected in the logs for that interval.")
        return 0

    offenders = [ip for ip, c in counts.items() if c >= args.threshold]
    if not offenders:
        print(f"✅ No IP is above the threshold of {args.threshold}.")
        return 0

    print(f"🚫 Suspicious IPs (above {args.threshold} requests): {offenders}")
    send_discord_message(args.discord_webhook, f"🚫 Blocked IPs on {args.filter_host}: {', '.join(offenders)}")

    for ip in offenders:
        yaml_text = build_policy_yaml(ip, args.selector_namespace)
        print("\n--- POLICY ---\n", yaml_text)
        if args.apply and not args.dry_run:
            rc, out, err = apply_policy(yaml_text)
            print(f"kubectl rc={rc}")
            if rc == 0:
                send_discord_message(args.discord_webhook, f"✅ Successfully blocked {ip}")
            else:
                send_discord_message(args.discord_webhook, f"❌ Failed to block {ip}: {err}")

if __name__ == "__main__":
    main()
