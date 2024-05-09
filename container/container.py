import os
import shutil
import sys
import tarfile
import uuid

from utility import *

from .cgroup_manager import CgroupManager


class Container:
    def __init__(self, command, volume=None, resource_config={}, tty=False) -> None:
        if command is str:
            command = command.split()
        self.cmd = command
        cmd_path = shutil.which(self.cmd[0])
        if cmd_path is None:
            print(f"未找到命令 {' '.join(self.cmd)}")
            sys.exit(1)
        self.cmd[0] = cmd_path
        self.volume = volume
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
        self.new_work_space()
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
            if not self.tty:
                return
            os.waitpid(pid, 0)
            cgroup_manager.remove()
            self.delete_work_space()

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

    def volume_extract(self, volume):
        volume_path = volume.split(":")
        if len(volume_path) != 2:
            print("volume格式错误")
            sys.exit(1)
        return volume_path[0], volume_path[1]

    def new_work_space(self):
        root_url = os.path.join(base_path, "root")
        if os.path.exists(root_url):
            shutil.rmtree(root_url)
        os.mkdir(root_url, mode=0o777)
        # create lower
        busybox_path = os.path.join(base_path, "busybox.tar")
        lower_path = os.path.join(root_url, "lower")
        if not os.path.exists(lower_path):
            os.mkdir(lower_path, mode=0o777)
            with tarfile.open(busybox_path, "r") as tar:
                tar.extractall(lower_path)
        # create upper、worker
        upper_path = os.path.join(root_url, "upper")
        os.mkdir(upper_path, mode=0o777)
        work_path = os.path.join(root_url, "work")
        os.mkdir(work_path, mode=0o777)
        # mount overlayfs
        mnt_url = os.path.join(root_url, "merged")
        os.mkdir(mnt_url, mode=0o777)
        # mount -t overlay overlay -o lowerdir=lower1:lower2:lower3,upperdir=upper,workdir=work merged
        os.system(
            f"mount -t overlay overlay -o lowerdir={lower_path},upperdir={upper_path},workdir={work_path} {mnt_url}/"
        )
        os.chdir(mnt_url)
        # 如果指定了volume则还需要mount volume
        if self.volume:
            host_path, container_path = self.volume_extract(self.volume)
            container_path = container_path.strip("/")
            # 通过bind mount 将宿主机目录挂载到容器目录
            os.makedirs(host_path, mode=0o777, exist_ok=True)
            container_path = os.path.join(mnt_url, container_path)
            os.makedirs(container_path, mode=0o777, exist_ok=True)
            os.system(f"mount -o bind {host_path} {container_path}")

    def delete_work_space(self):
        root_url = os.path.join(base_path, "root")
        mnt_url = os.path.join(root_url, "merged")
        # 一定要要先 umount volume ，然后再删除目录，否则由于 bind mount 存在，删除临时目录会导致 volume 目录中的数据丢失
        if self.volume:
            host_path, container_path = self.volume_extract(self.volume)
            container_path = os.path.join(mnt_url, container_path.strip("/"))
            os.system(f"umount {container_path}")
        # unmount overlayfs：将../root/merged目录挂载解除
        os.system(f"umount {mnt_url}")
        shutil.rmtree(mnt_url)
        # 删除其他目录：删除之前为 overlayfs 准备的 upper、work、merged 目录
        upper_path = os.path.join(root_url, "upper")
        shutil.rmtree(upper_path)
        work_path = os.path.join(root_url, "work")
        shutil.rmtree(work_path)

    @staticmethod
    def commit(image_name):
        mnt_url = os.path.join(base_path, "root", "merged")
        image_url = os.path.join(base_path, "root", f"{image_name}.tar")
        with tarfile.open(image_url, "w") as tar:
            tar.add(mnt_url, arcname=".")
