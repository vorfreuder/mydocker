import ipaddress
import json
import os

ipam_default_allocator_path = os.path.join(os.path.dirname(__file__), "subnet.json")


class IPAM:
    def __init__(self, subnet_allocator_path=ipam_default_allocator_path) -> None:
        self.subnet_allocator_path = subnet_allocator_path

    def load(self):
        if not os.path.exists(self.subnet_allocator_path):
            self.subnets = {}
            return
        with open(self.subnet_allocator_path, "r") as f:
            self.subnets = json.load(f)

    def dump(self):
        with open(self.subnet_allocator_path, "w") as f:
            json.dump(self.subnets, f, indent=4)

    def allocate(self, subnet):
        self.load()
        subnet = ipaddress.ip_network(subnet, strict=True)
        if subnet.with_prefixlen not in self.subnets:
            self.subnets[subnet.with_prefixlen] = []
        for ip in subnet.hosts():
            if str(ip) not in self.subnets[subnet.with_prefixlen]:
                self.subnets[subnet.with_prefixlen].append(str(ip))
                self.dump()
                return ipaddress.ip_interface(str(ip) + "/" + str(subnet.prefixlen))
        else:
            return None

    def release(self, subnet, ip):
        self.load()
        subnet = ipaddress.ip_network(subnet, strict=True)
        if (
            subnet.with_prefixlen in self.subnets
            and ip in self.subnets[subnet.with_prefixlen]
        ):
            self.subnets[subnet.with_prefixlen].remove(ip)
            self.dump()
            return True
        else:
            return False


if __name__ == "__main__":
    ipam = IPAM()
    subnet = "192.168.0.0/24"
    subnet = ipaddress.ip_network(subnet, strict=True)
    ip = ipam.allocate(subnet)
    print(str(ip.ip))
    print(f"ip addr add {ip} dev")
    print(ipam.release(subnet, "192.168.0.51"))
