import sys
from cli.commands import handle_command

def main():
    if len(sys.argv) < 2:
        print("Usage: docksmith <command>")
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    handle_command(command, args)

if __name__ == "__main__":
    main()