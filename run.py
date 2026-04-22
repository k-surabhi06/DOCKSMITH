#!/usr/bin/env python3
"""
DOCKSMITH Runner - Easy wrapper for common tasks
"""
import subprocess
import sys
import os

def run_docksmith(args):
    """Run docksmith command with proper sudoers handling for run."""
    if not args:
        print("Usage: ./run.py <command> [args...]")
        print("  build -t name:tag context [--no-cache]")
        print("  run name:tag [cmd] [-e KEY=VALUE ...]")
        print("  images")
        print("  rmi name:tag")
        return 1
    
    command = args[0]
    
    # Run command needs sudo with -E flag to preserve environment
    if command == "run":
        cmd = ["sudo", "-E", "python3", "main.py"] + args
    else:
        cmd = ["python3", "main.py"] + args
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_docksmith(sys.argv[1:]))
