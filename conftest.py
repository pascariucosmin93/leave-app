#!/usr/bin/env python3
import subprocess
import re
import requests
import os

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def send_discord_message(message):
    """Send a Discord notification only when a webhook is configured."""
    if not DISCORD_WEBHOOK:
        print("⚠️  No Discord webhook configured.")
        return
    try:
        resp = requests.post(DISCORD_WEBHOOK, json={"content": message}, timeout=10)
        if resp.status_code >= 300:
            print(f"⚠️ Discord error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ Failed to send Discord message: {e}")

def list_blocked_policies():
    """Return the list of GlobalNetworkPolicy objects matching block-*."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "globalnetworkpolicy", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            print("❌ Error listing policies:", result.stderr.strip())
            send_discord_message(f"❌ Failed to list GlobalNetworkPolicy resources: {result.stderr.strip()}")
            return []

        policies = []
        for line in result.stdout.splitlines():
            name = line.split()[0]
            if name.startswith("block-"):
                policies.append(name)
        return policies
    except Exception as e:
        send_discord_message(f"❌ Failed to query Calico: {e}")
        return []

def delete_policy(name):
    """Delete a block-* policy and notify Discord."""
    try:
        subprocess.run(["kubectl", "delete", "globalnetworkpolicy", name], check=True, timeout=10)
        ip = name.replace("block-", "").replace("-", ".")
        print(f"🧹 Deleted {name} (IP: {ip})")
        send_discord_message(f"🧹 unblocked IP: `{ip}`")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to delete {name}: {e}")
        send_discord_message(f"❌ Failed to delete rule `{name}`: {e}")
    except Exception as e:
        print(f"❌ Unexpected error deleting {name}: {e}")
        send_discord_message(f"❌ Unexpected error while deleting rule `{name}`: {e}")

def main():
    policies = list_blocked_policies()
    if not policies:
        print("✅ No blocked IPs found. Nothing to clean.")
        return

    print(f"🧹 Found {len(policies)} blocked IPs to delete.")
    for name in policies:
        delete_policy(name)

if __name__ == "__main__":
    main()
