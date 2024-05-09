import argparse
import os
import shutil
import tarfile

from container import *

parser = argparse.ArgumentParser(
    # prog="mydocker",
    description="A simple docker implementation based on python3"
)
subparsers = parser.add_subparsers(dest="subcommand")
run_parser = subparsers.add_parser(
    "run",
    help="Create a container with namespace and cgroups limit",
)
run_parser.add_argument(
    # 简单起见，这里把 -i 和 -t 参数合并成一个
    "-it",
    action="store_true",
    help="enable tty",
)
run_parser.add_argument(
    # 限制进程内存使用量
    "-mem",
    default=None,
    help="memory limit, at least greater than 6m, e.g.: -mem 100m",
)
run_parser.add_argument(
    # 限制进程 cpu 使用率
    "-cpu",
    type=float,
    default=None,
    help="cpu quota,e.g.: -cpu 0.8",
)
run_parser.add_argument(
    # 限制进程 cpu 使用率
    "-cpuset",
    default=None,
    help="cpuset limit,e.g.: -cpuset 2,4",
)
run_parser.add_argument(
    "command",
    nargs="+",
    help="Command to run in the container",
)

init_parser = subparsers.add_parser(
    "init",
    help="Init container process run user's process in container. Do not call it outside",
)
init_parser.add_argument(
    "command",
    nargs="+",
    help="Command to run in the container",
)
args = parser.parse_args()
print(args)
if args.subcommand == "run":
    con = Container(
        args.command,
        {"cpu": args.cpu, "cpuset": args.cpuset, "mem": args.mem},
        args.it,
    )
    con.run()
elif args.subcommand == "init":
    con = Container(args.command)
    con.init()
