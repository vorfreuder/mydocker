import os


class Subsystem:
    def __init__(self) -> None:
        pass

    def set(self, cgroup_path, resource_config):
        pass

    def apply(self, cgroup_path, pid):
        path = os.path.join(self.get_cgroup_path(cgroup_path, False), "cgroup.procs")
        if not os.path.exists(path):
            return
        with open(path, "w") as f:
            f.write(str(pid))

    def remove(self, cgroup_path):
        path = self.get_cgroup_path(cgroup_path, False)
        if os.path.exists(path):
            os.rmdir(path)

    def get_cgroup_path(self, cgroup_path, auto_create=True):
        res_path = os.path.join("/sys/fs/cgroup", cgroup_path)
        if auto_create:
            os.makedirs(res_path, mode=0o755, exist_ok=True)
        return res_path


class CpuSubsystem(Subsystem):
    def set(self, cgroup_path, resource_config):
        if resource_config.get("cpu") is None:
            return
        with open(os.path.join(self.get_cgroup_path(cgroup_path), "cpu.max"), "w") as f:
            f.write(f"{float(resource_config['cpu'])*100000} 100000")


class MemorySubsystem(Subsystem):
    def set(self, cgroup_path, resource_config):
        if resource_config.get("mem") is None:
            return
        path = self.get_cgroup_path(cgroup_path)
        with open(os.path.join(path, "memory.max"), "w") as f:
            f.write(resource_config["mem"])
        # 由于swap，即使超过了内存限制，也不会杀死进程，只是会将进程的内存交换到swap分区，这里直接简单设置为0
        with open(os.path.join(path, "memory.swap.max"), "w") as f:
            f.write("0")


class CpusetSubSystem(Subsystem):
    def set(self, cgroup_path, resource_config):
        if resource_config.get("cpuset") is None:
            return
        with open(
            os.path.join(self.get_cgroup_path(cgroup_path), "cpuset.cpus"), "w"
        ) as f:
            f.write(resource_config["cpuset"])


if __name__ == "__main__":
    cgroup_path = "xxxx-xxxx-xxxx-xxxx"
    cpu_sub = CpuSubsystem()
    print(cpu_sub.get_cgroup_path(cgroup_path))
    print("pid:", os.getpid())
    cpu_sub.set(cgroup_path, {"cpu": 0.75})
    cpu_sub.apply(cgroup_path, os.getpid())

    mem_sub = MemorySubsystem()
    mem_sub.set(cgroup_path, {"mem": "100m"})
    mem_sub.apply(cgroup_path, os.getpid())

    cpuset_sub = CpusetSubSystem()
    cpuset_sub.set(cgroup_path, {"cpuset": "10,0"})
    cpuset_sub.apply(cgroup_path, os.getpid())
    while True:
        pass
