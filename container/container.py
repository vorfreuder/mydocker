import os
import shutil
import sys
import uuid

from .cgroup_manager import CgroupManager
from .libc import MS_NODEV, MS_NOEXEC, MS_NOSUID, MS_PRIVATE, MS_REC, mount


class Container:
    def __init__(self, command, resource_config={}, tty=True) -> None:
        if command is str:
            command = command.split()
        self.cmd = command
        cmd_path = shutil.which(self.cmd[0])
        if cmd_path is None:
            print(f"未找到命令 {' '.join(self.cmd)}")
            sys.exit(1)
        self.cmd[0] = cmd_path
        self.resource_config = resource_config
        self.tty = tty
        self.id = str(uuid.uuid4())

    def run(self):
        f = open("/proc/self/cmdline")
        cmd = f.read().split("\x00")[:2]
        f.close()
        cmd.append("init")
        cmd.append("--")  # 用于区分命令
        cmd.extend(self.cmd)

        print("id:", self.id)
        # cgroup限制资源
        cgroup_manager = CgroupManager(self.id)
        os.unshare(
            os.CLONE_NEWUTS
            | os.CLONE_NEWPID
            | os.CLONE_NEWNS
            | os.CLONE_NEWNET
            | os.CLONE_NEWIPC
            # | os.CLONE_NEWUSER
        )
        pid = os.fork()
        print(f"[*] fork pid: {pid}")
        if pid == 0:
            if not self.tty:
                print("not tty")
                null_fd = os.open("/dev/null", os.O_RDWR)
                os.dup2(null_fd, 0)  # 重定向标准输入
                os.dup2(null_fd, 1)  # 重定向标准输出
                os.dup2(null_fd, 2)  # 重定向标准错误
                os.close(null_fd)
            cgroup_manager.set(self.resource_config)
            cgroup_manager.apply(pid)
            os.execve(cmd[0], cmd, os.environ)
        else:
            # 还原父进程的命名空间
            for ns_file in ["ipc", "mnt", "net", "pid", "uts"]:
                ns_path = os.path.join("/proc/1/ns/", ns_file)
                fd = os.open(ns_path, os.O_RDONLY)
                os.setns(fd)
                os.close(fd)
            print(f"[*] child pid: {pid}")
            os.waitpid(pid, 0)
            print(f"[*] child exit")
            cgroup_manager.remove()

    def init(self):
        mount("", "/", "", MS_PRIVATE | MS_REC, "")
        mount("none", "/proc", "proc", MS_NOEXEC | MS_NOSUID | MS_NODEV)
        cmd = self.cmd
        os.execve(cmd[0], cmd, os.environ)
