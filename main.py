import sys
import os
from pathlib import Path

# Add project directory to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cli.commands import handle_command

def main():
    if len(sys.argv) < 2:
        print("Usage: docksmith <command>")
        print("\nCommands:")
        print("  build -t <name:tag> <context> [--no-cache]  Build an image")
        print("  images                                       List images")
        print("  rmi <name:tag>                              Remove image")
        print("  run <name:tag> [cmd] [-e KEY=VALUE ...]    Run a container")
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    handle_command(command, args)

if __name__ == "__main__":
    main()