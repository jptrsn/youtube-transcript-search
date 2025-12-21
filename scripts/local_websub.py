#!/usr/bin/env python3
"""
Local WebSub management script - manages WebSub subscriptions using local network
and writes to remote DB via SSH tunnel
"""

import argparse
import sys
import os
import json
from pathlib import Path

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fabric import Connection
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env.prod from the project root
env_path = Path(__file__).parent.parent / '.env.prod'
load_dotenv(env_path)

# Get credentials
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')

from backend.services.websub_service import WebSubService

def get_postgres_ip(conn):
    """Get the IP address of the postgres container"""
    result = conn.run('docker inspect yt-transcript-db', hide=True)
    inspect_data = json.loads(result.stdout)
    networks = inspect_data[0]['NetworkSettings']['Networks']
    ip_address = list(networks.values())[0]['IPAddress']
    return ip_address

def main():
    parser = argparse.ArgumentParser(description='Manage WebSub subscriptions for YouTube channels')
    parser.add_argument('--ssh-host', required=True, help='SSH host (VPS IP or hostname)')
    parser.add_argument('--ssh-user', default='root', help='SSH username (default: root)')
    parser.add_argument('--ssh-key', default=None, help='SSH private key path (default: auto-detect)')
    parser.add_argument('--operation', required=True,
                        choices=['subscribe', 'unsubscribe', 'status', 'list', 'renew'],
                        help='Operation to perform')
    parser.add_argument('--channel', help='Channel ID (e.g., UCxxx) - required for subscribe/unsubscribe/status')

    args = parser.parse_args()

    # Validate channel argument for operations that need it
    if args.operation in ['subscribe', 'unsubscribe', 'status'] and not args.channel:
        parser.error(f"--channel is required for operation '{args.operation}'")

    print(f"🔌 Connecting to {args.ssh_host}...")

    try:
        # Create SSH connection
        connect_kwargs = {}
        if args.ssh_key:
            connect_kwargs["key_filename"] = args.ssh_key

        conn = Connection(
            host=args.ssh_host,
            user=args.ssh_user,
            connect_kwargs=connect_kwargs
        )

        # Detect postgres container IP
        print(f"🔍 Detecting postgres container IP...")
        postgres_ip = get_postgres_ip(conn)
        print(f"✓ Found postgres at {postgres_ip}")

        # Create port forward (SSH tunnel)
        with conn.forward_local(5433, remote_host=postgres_ip, remote_port=5432):
            print(f"✓ SSH tunnel established (local port 5433)\n")

            # Create database connection through tunnel
            db_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5433/{POSTGRES_DB}"
            engine = create_engine(db_url)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            print(f"✓ Connected to remote database\n")

            # Create WebSub service
            service = WebSubService(db)

            # Execute operation
            if args.operation == 'subscribe':
                print(f"📡 Subscribing to channel {args.channel}...\n")
                result = service.subscribe_to_channel(args.channel)
                print(f"✅ {result['message']}")
                if result.get('subscription'):
                    sub = result['subscription']
                    print(f"\nSubscription Details:")
                    print(f"  Channel: {sub['channel_name']}")
                    print(f"  Status: {sub['status']}")
                    print(f"  Expires: {sub['expires_at'] or 'Pending verification'}")

            elif args.operation == 'unsubscribe':
                print(f"🔕 Unsubscribing from channel {args.channel}...\n")
                result = service.unsubscribe_from_channel(args.channel)
                print(f"✅ {result['message']}")

            elif args.operation == 'status':
                print(f"📊 Getting subscription status for {args.channel}...\n")
                status = service.get_subscription_status(args.channel)
                if status:
                    print(f"Channel: {status['channel_name']}")
                    print(f"Status: {status['status']}")
                    print(f"Subscribed: {status['subscribed_at'] or 'N/A'}")
                    print(f"Expires: {status['expires_at'] or 'N/A'}")
                    print(f"Lease: {status['lease_seconds']} seconds" if status['lease_seconds'] else 'Lease: N/A')
                    print(f"Last notification: {status['last_notification_at'] or 'Never'}")
                    if status['last_error']:
                        print(f"Last error: {status['last_error']}")
                else:
                    print(f"❌ No subscription found for channel {args.channel}")

            elif args.operation == 'list':
                print(f"📋 Listing all WebSub subscriptions...\n")
                subscriptions = service.list_all_subscriptions()
                if not subscriptions:
                    print("No subscriptions found")
                else:
                    print(f"Total subscriptions: {len(subscriptions)}\n")
                    for sub in subscriptions:
                        status_icon = {
                            'active': '✅',
                            'pending': '⏳',
                            'expired': '⏰',
                            'failed': '❌'
                        }.get(sub['status'], '❓')

                        print(f"{status_icon} {sub['channel_name']} ({sub['channel_id']})")
                        print(f"   Status: {sub['status']}")
                        if sub['expires_at']:
                            print(f"   Expires: {sub['expires_at']}")
                        if sub['last_notification_at']:
                            print(f"   Last notification: {sub['last_notification_at']}")
                        print()

            elif args.operation == 'renew':
                print(f"🔄 Renewing expiring subscriptions...\n")
                result = service.renew_expiring_subscriptions(hours_before_expiry=24)
                if result['success']:
                    print(f"✅ Renewal complete:")
                    print(f"   Total expiring: {result['total_expiring']}")
                    print(f"   Renewed: {result['renewed']}")
                    print(f"   Failed: {result['failed']}")
                else:
                    print(f"❌ Renewal failed: {result.get('message', 'Unknown error')}")

            db.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()