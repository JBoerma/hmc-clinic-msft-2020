import argparse
from typing import List


def getArguments() -> "ArgsHolder":
    namespace = parseArguments()
    return ArgsHolder(namespace=namespace)


# Adding this class enables us to pre-process arguments
class ArgsHolder: 
    def __init__(self, namespace: argparse.Namespace): 
        self.device: str             = namespace.device 
        self.options_list: List[str] = [x.strip() for x in namespace.options.split(",")]


def parseArguments() -> argparse.Namespace: 
    parser = argparse.ArgumentParser(
        description="Run H2/H3 Experiment",
        epilog="Usage:..."
    )
    parser.add_argument(
        "--device",
        help=(  "network device modified by tc command.\n" 
                "default:\"%(default)s\""),
        default="lo root",
    )

    parser.add_argument(
        "--options",
        help=(  "NetEm options, comma-separated OPTIONS as specified by \"man netem\".\n" 
                "default:\"%(default)s\""),
        default="delay 100ms 10ms 25%",
    )

    return parser.parse_args()
