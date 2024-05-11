import argparse

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
run_group = run_parser.add_mutually_exclusive_group()
run_group.add_argument(
    # 简单起见，这里把 -i 和 -t 参数合并成一个
    "-it",
    action="store_true",
    help="enable tty",
)
run_group.add_argument(
    # 后台运行容器
    "-d",
    action="store_true",
    help="detach container",
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
    # 数据卷
    "-v",
    default=None,
    help="volume,e.g.: -v /ect/conf:/etc/conf",
)
run_parser.add_argument(
    "-name",
    default=None,
    help="container name",
)
run_parser.add_argument(
    "image_name",
    help="image name,e.g.: busybox.tar",
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

commit_parser = subparsers.add_parser("commit", help="commit container to image")
commit_parser.add_argument("container_id")
commit_parser.add_argument("image_name")

ps_parser = subparsers.add_parser("ps", help="list all the containers")

logs_parser = subparsers.add_parser("logs", help="print logs of a container")
logs_parser.add_argument("container_id")

exec_parser = subparsers.add_parser("exec", help="exec a command into container")
exec_parser.add_argument("container_id")
exec_parser.add_argument("command", nargs="+")

stop_parser = subparsers.add_parser("stop", help="stop a container")
stop_parser.add_argument("container_id")

rm_parser = subparsers.add_parser("rm", help="remove unused containers")
rm_parser.add_argument("-f", action="store_true", help="force delete running container")
rm_parser.add_argument("container_id")

args = parser.parse_args()
print(args)
if args.subcommand == "run":
    con = Container(
        args.command,
        args.image_name,
        args.name,
        args.v,
        {"cpu": args.cpu, "cpuset": args.cpuset, "mem": args.mem},
        args.it,
    )
    con.run()
elif args.subcommand == "init":
    con = Container(args.command)
    con.init()
elif args.subcommand == "commit":
    Container.commit(args.container_id, args.image_name)
elif args.subcommand == "ps":
    Container.ps()
elif args.subcommand == "logs":
    Container.logs(args.container_id)
elif args.subcommand == "exec":
    Container.exec(args.container_id, args.command)
elif args.subcommand == "stop":
    Container.stop(args.container_id)
elif args.subcommand == "rm":
    Container.rm(args.container_id, args.f)
