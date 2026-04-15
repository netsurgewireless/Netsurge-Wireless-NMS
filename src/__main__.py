#!/usr/bin/env python
"""Main launcher for Network Monitor Desktop Applications."""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description='Netsurge Wireless NMS')
    parser.add_argument('mode', nargs='?', choices=['server', 'client', 'launcher'],
                        help='Application mode: server, client, or launcher (desktop GUI)')
    parser.add_argument('--server', default='http://localhost:8080',
                        help='Server URL for client mode')
    parser.add_argument('--port', type=int, default=8080,
                        help='Server port')
    
    args = parser.parse_args()
    
    if args.mode == 'server' or not args.mode:
        from src.server import main as server_main
        sys.exit(server_main())
    elif args.mode == 'client':
        from src.client import main as client_main
        sys.exit(client_main())
    elif args.mode == 'launcher':
        from src.desktop_launcher import main as launcher_main
        launcher_main()
    else:
        from src.desktop_launcher import main as launcher_main
        launcher_main()


if __name__ == "__main__":
    main()
