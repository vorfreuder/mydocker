import os
import sys


class Subsystem:
    def __init__(self) -> None:
        pass

    def set(self, cgroup_path, resource_config):
        pass

    def apply(self, cgroup_path, pid):
        path = os.path.join(self.get_cgroup_path(cgroup_path, False), "tasks")
        if not os.path.exists(path):
            return
        with open(path, "w") as f:
            f.write(str(pid))

    def remove(self, cgroup_path):
        path = self.get_cgroup_path(cgroup_path, False)
        if os.path.exists(path):
            os.rmdir(path)

    def get_cgroup_path(self, cgroup_path, auto_create=True):
        res_path = None
        mount_point_index = 4
        with open("/proc/self/mountinfo") as f:
            for line in f:
                fields = line.split()
                subsystems = fields[-1].split(",")
                if self.subsystem_name in subsystems:
                    res_path = fields[mount_point_index]
                    break
                if res_path is not None:
                    break
        if res_path is None:
            print(f"Failed to find cgroup {self.subsystem_name}")
            sys.exit(1)
        res_path = os.path.join(res_path, cgroup_path)
        if auto_create:
            os.makedirs(res_path, mode=0o755, exist_ok=True)
        return res_path


class CpuSubsystem(Subsystem):
    def __init__(self):
        super().__init__()
        self.subsystem_name = "cpu"

    def set(self, cgroup_path, resource_config):
        if resource_config.get("cpu") is None:
            return
        path = self.get_cgroup_path(cgroup_path)
        with open(os.path.join(path, "cpu.cfs_period_us"), "w") as f:
            f.write("100000")
        with open(os.path.join(path, "cpu.cfs_quota_us"), "w") as f:
            f.write(str(int(resource_config["cpu"] * 100000)))


class MemorySubsystem(Subsystem):
    def __init__(self):
        super().__init__()
        self.subsystem_name = "memory"

    def set(self, cgroup_path, resource_config):
        if resource_config.get("mem") is None:
            return
        path = self.get_cgroup_path(cgroup_path)
        with open(
            os.path.join(path, "memory.limit_in_bytes"),
            "w",
        ) as f:
            f.write(resource_config["mem"])
        # 由于memory.swappiness，即使超过了内存限制，也不会杀死进程，只是会将进程的内存交换到swap分区，这里直接简单设置为0
        with open(os.path.join(path, "memory.swappiness"), "w") as f:
            f.write("0")


class CpusetSubSystem(Subsystem):
    def __init__(self):
        super().__init__()
        self.subsystem_name = "cpuset"

    def set(self, cgroup_path, resource_config):
        if resource_config.get("cpuset") is None:
            return
        path = self.get_cgroup_path(cgroup_path)
        with open(os.path.join(path, "cpuset.cpus"), "w") as f:
            f.write(resource_config["cpuset"])
        # 还要对cpuset.mems进行设置，不然之后无法将pid加入到tasks中
        with open(os.path.join(path, "cpuset.mems"), "w") as f:
            f.write("0-1")


if __name__ == "__main__":
    cgroup_path = "mydock"
    cpu_sub = CpuSubsystem()
    print(cpu_sub.get_cgroup_path(cgroup_path, False))
    print("pid:", os.getpid())
    cpu_sub.set(cgroup_path, {"cpu": 0.87})
    cpu_sub.apply(cgroup_path, os.getpid())

    mem_sub = MemorySubsystem()
    mem_sub.set(cgroup_path, {"mem": "5m"})
    mem_sub.apply(cgroup_path, os.getpid())

    cpuset_sub = CpusetSubSystem()
    cpuset_sub.set(cgroup_path, {"cpuset": "55"})
    cpuset_sub.apply(cgroup_path, os.getpid())
    while True:
        pass
