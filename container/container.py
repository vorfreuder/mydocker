import os
import shutil
import sys
import uuid

from .cgroup_manager import CgroupManager
from .libc import (
    MNT_DETACH,
    MS_BIND,
    MS_NODEV,
    MS_NOEXEC,
    MS_NOSUID,
    MS_PRIVATE,
    MS_REC,
    MS_STRICTATIME,
    mount,
    pivot_root,
    umount,
)


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
            os.waitpid(pid, 0)
            cgroup_manager.remove()

    def init(self):
        self.setUpMount()
        cmd = self.cmd
        os.execve(cmd[0], cmd, os.environ)

    def setUpMount(self):
        # systemd 加入linux之后, mount namespace 就变成 shared by default, 所以你必须显示
        # 声明你要这个新的mount namespace独立。
        # 如果不先做 private mount，会导致挂载事件外泄，后续执行 pivotRoot 会出现 invalid argument 错误
        mount("", "/", "", MS_PRIVATE | MS_REC)
        self.pivotRoot(os.getcwd())
        # mount /proc
        mount("none", "/proc", "proc", MS_NOEXEC | MS_NOSUID | MS_NODEV)
        # 由于前面 pivotRoot 切换了 rootfs，因此这里重新 mount 一下 /dev 目录
        # tmpfs 是基于 件系 使用 RAM、swap 分区来存储。
        # 不挂载 /dev，会导致容器内部无法访问和使用许多设备，这可能导致系统无法正常工作
        mount("tmpfs", "/dev", "tmpfs", MS_NOSUID | MS_STRICTATIME)

    def pivotRoot(self, root):
        # 注意：PivotRoot调用有限制，newRoot和oldRoot不能在同一个文件系统下。
        # 因此，为了使当前root的老root和新root不在同一个文件系统下，这里把root重新mount了一次。
        # bind mount是把相同的内容换了一个挂载点的挂载方法
        mount(root, root, "bind", MS_BIND | MS_REC)
        # 创建 rootfs/.pivot_root 目录用于存储 old_root
        pivotDir = os.path.join(root, ".pivot_root")
        os.mkdir(pivotDir, mode=0o777)
        # 执行pivot_root调用,将系统rootfs切换到新的rootfs,
        # PivotRoot调用会把 old_root挂载到pivotDir,也就是rootfs/.pivot_root,挂载点现在依然可以在mount命令中看到
        pivot_root(root, pivotDir)
        # 修改当前的工作目录到根目录
        os.chdir("/")
        # 最后再把old_root umount了，即 umount rootfs/.pivot_root
        # 由于当前已经是在 rootfs 下了，就不能再用上面的rootfs/.pivot_root这个路径了,现在直接用/.pivot_root这个路径即可
        pivotDir = os.path.join("/", ".pivot_root")
        # umount(pivotDir, MNT_DETACH)不知道为什么会导致后面没法挂载/proc
        os.system(f"umount {pivotDir} -l")
        os.rmdir(pivotDir)
