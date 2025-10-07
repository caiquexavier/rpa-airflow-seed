#!/usr/bin/env python3
"""
RPA Listener - entrypoint

This module only delegates to controllers under `src`.
"""

import sys


def main():
    try:
        from src.controllers.listener_controller import ListenerController
        ListenerController().run()
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as exc:
        # Avoid pulling in logging setup here to keep this file minimal
        sys.stderr.write(f"Fatal error: {exc}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
