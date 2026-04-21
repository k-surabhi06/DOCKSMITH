#!/usr/bin/env python3
"""
Sample application that demonstrates Docksmith functionality.
Prints a greeting with environment variables.
"""
import os
import sys

def main():
    app_name = os.environ.get("APP_NAME", "MyApp")
    message = os.environ.get("MESSAGE", "HelloFromDocksmith")
    workdir = os.getcwd()
    
    print(f"=== {app_name} ===")
    print(f"Message: {message}")
    print(f"Working Directory: {workdir}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Process ID: {os.getpid()}")
    print("All environment variables:")
    for key in sorted(os.environ.keys()):
        if key.startswith(("APP_", "MESSAGE")):
            print(f"  {key}={os.environ[key]}")
    print("\nExecution completed successfully!")

if __name__ == "__main__":
    main()
