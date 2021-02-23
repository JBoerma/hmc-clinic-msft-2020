import argparse # TODO: docopt
from typing import List


def getArguments() -> "ArgsHolder":
    namespace = parseArguments()
    return ArgsHolder(namespace=namespace)


# Adding this class enables us to pre-process arguments
class ArgsHolder: 
    def __init__(self, namespace: argparse.Namespace): 
        self.device: str             = namespace.device 
        self.options_list: List[str] = [x.strip() for x in namespace.options.split(",")]
        self.browsers: List[str]     = namespace.browsers
        self.url: str                = namespace.url
        self.runs: int               = namespace.runs
        self.payloads: List[str]     = namespace.payloads


def parseArguments() -> argparse.Namespace: 
    parser = argparse.ArgumentParser(
        description="Run H2/H3 Experiment",
        epilog="Usage:..."
    )

    parser.add_argument(
        "--device",
        help=(
            "network device modified by tc command.\n" 
            "default:\"%(default)s\""
        ),
        default="lo root",
    )

    parser.add_argument(
        "--options",
        help=(
            "NetEm options, comma-separated OPTIONS as specified by \"man netem\".\n" 
            "default:\"%(default)s\""
        ),
        default="delay 100ms 10ms 25%",
    )

    parser.add_argument(
        "--browsers",
        choices={"firefox", "chromium", "edge"},
        nargs="*",
        help=(
            "Browsers used in experiment.\n"
            "default:\"firefox chromium edge\""
        ),
        default=["firefox"],  # TODO - edge and chrome fail
    )

    parser.add_argument(
        "--url",
        help=(
            "URL for resource fetched in experiment.\n"
            "default:\"%(default)s\""
        ),
        default="https://localhost",  # TODO - "version" header is not returned by most browsers, results in error!
    )

    parser.add_argument(
        "--runs",
        type=int,
        help=(
            "Integer: Specify number of runs for experiment.\n"
            "default:\"%(default)s\""
        ),
        default=10,
    )

    parser.add_argument(
         "--sync",
        type=bool,
        help=(
            "Boolean: if run the experiment synchronously.\n"
            "default:\"%(default)s\""
        ),
        default=True,
    )

    parser.add_argument(
        "--payloads",
        type=List[str],
        choices={"1kb", "5kb", "10kb", "50kb", "100kb", "500kb", "1mb"},
        nargs="*",
        help=(
            "The size of the requsting payload.\n"
            "default:\"100kb\""
        ),
        default=["100kb"],
    )

    return parser.parse_args()
