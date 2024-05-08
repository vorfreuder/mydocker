import subprocess


class CgroupManager:
    def __init__(self, cgroup_path) -> None:
        # stat -fc %T /sys/fs/cgroup/ 如果输出是cgroup2fs 那就是v2; 如果输出是tmpfs 那就是v1
        # 如果宿主机是WSL2, 在/etc/wsl.conf加上
        # [boot]
        # systemd=true
        self.cgroup_path = cgroup_path
        cgroup_version = (
            subprocess.check_output("stat -fc %T /sys/fs/cgroup/", shell=True)
            .decode()
            .strip()
        )
        if cgroup_version == "cgroup2fs":
            self.cgroup_version = 2
            from .cgroups2 import CpusetSubSystem, CpuSubsystem, MemorySubsystem
        else:
            self.cgroup_version = 1
            from .cgroups1 import CpusetSubSystem, CpuSubsystem, MemorySubsystem
        self.subsystems = [CpuSubsystem(), MemorySubsystem(), CpusetSubSystem()]

    def set(self, resource_config):
        for sub in self.subsystems:
            sub.set(self.cgroup_path, resource_config)

    def apply(self, pid):
        for sub in self.subsystems:
            sub.apply(self.cgroup_path, pid)

    def remove(self):
        for sub in self.subsystems:
            sub.remove(self.cgroup_path)
