import ipaddress
import json
import os

from tabulate import tabulate
from utility import shell

from .bridge_network_driver import BridgeNetworkDriver
from .ipam import IPAM

default_network_path = os.path.join(os.path.dirname(__file__), "networks.json")


class Network:
    @staticmethod
    def init():
        return {BridgeNetworkDriver.name: BridgeNetworkDriver}

    @staticmethod
    def load(path=default_network_path):
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            data = json.load(f)
        return data

    @staticmethod
    def dump(path, name, data):
        networks = Network.load(path)
        networks[name] = data
        if data is None:
            del networks[name]
        with open(path, "w") as f:
            json.dump(networks, f, indent=4)

    @staticmethod
    def create(name, subnet, driver):
        drivers = Network.init()
        if driver not in drivers:
            raise Exception(f"Driver {driver} not found")
        subnet = ipaddress.ip_network(subnet, strict=True)
        ip_interface = IPAM().allocate(subnet)
        drivers[driver].create(subnet, ip_interface, name)
        Network.dump(
            default_network_path,
            name,
            {
                "NAME": name,
                "IpRange": str(subnet),
                "IP": str(ip_interface.ip),
                "Driver": driver,
            },
        )

    @staticmethod
    def connect(network_name, container_info):
        if network_name is None:
            return
        drivers = Network.init()
        # 从networks字典中取到容器连接的网络的信息，networks字典中保存了当前己经创建的网络
        networks = Network.load()
        if network_name not in networks:
            raise Exception(f"Network {network_name} not found")
        network = networks[network_name]
        # 分配容器IP地址
        ip_interface = IPAM().allocate(network["IpRange"])
        # 创建网络端点
        endpoint = {
            "ID": container_info["ID"],
            "IPINTERFACE": ip_interface,
            "PORTMAPPING": container_info["PORTMAPPING"],
        }
        container_info["IP"] = ip_interface.ip
        # 调用网络驱动挂载和配置网络端点
        drivers[network["Driver"]].connect(network, endpoint)
        # 到容器的namespace配置容器网络设备IP地址
        Network.config_endpoint_ip_address_and_route(network, endpoint, container_info)
        # 配置端口映射信息，例如 mydocker run -p 8080:80
        Network.config_port_mapping(endpoint)

    @staticmethod
    def config_endpoint_ip_address_and_route(network, endpoint, container_info):
        peer_veth_name = endpoint["PEERNAME"]
        # 将容器的网络端点加入到容器的网络空间中
        command = f"ip link set {peer_veth_name} netns {container_info['PID']}"
        shell(command)
        # 设置容器端口IP地址
        command = f"nsenter -t {container_info['PID']} -n -- ip addr add {endpoint['IPINTERFACE']} dev {peer_veth_name}"
        shell(command)
        # 启动容器端口
        command = f"nsenter -t {container_info['PID']} -n -- ip link set dev {peer_veth_name} up"
        shell(command)
        # 启动lo
        command = f"nsenter -t {container_info['PID']} -n -- ip link set lo up"
        shell(command)
        # 设置容器端口默认路由
        command = f"nsenter -t {container_info['PID']} -n -- ip route add default via {network['IP']}"
        shell(command)

    @staticmethod
    def config_port_mapping(endpoint):
        if endpoint["PORTMAPPING"] is None:
            return
        # iptables -t filter -L 一般缺省策略都是 ACCEPT，不需要改动，如果如果缺省策略是DROP，需要设置为ACCEPT：
        shell("iptables -t filter -P FORWARD ACCEPT")
        for port_mapping in endpoint["PORTMAPPING"]:
            host_port, container_port = port_mapping.split(":")
            endpoint_ip = endpoint["IPINTERFACE"].ip
            command = f"iptables -t nat -A PREROUTING -p tcp -m tcp --dport {host_port} -j DNAT --to-destination {endpoint_ip}:{container_port}"
            shell(command)

    @staticmethod
    def list():
        networks = Network.load()
        table = []
        for name, info in networks.items():
            table.append([name, info["IpRange"], info["Driver"]])
        print(tabulate(table, headers=["NAME", "IPRANGE", "DRIVER"]))

    @staticmethod
    def remove(network_name):
        networks = Network.load()
        if network_name not in networks:
            raise Exception(f"Network {network_name} not found")
        network = networks[network_name]
        # 清除 iptables 规则
        command = f"iptables -t nat -D POSTROUTING -s {network['IpRange']} ! -o {network_name} -j MASQUERADE"
        shell(command)
        # 删除网桥
        drivers = Network.init()
        driver = network["Driver"]
        if driver not in drivers:
            raise Exception(f"Driver {driver} not found")
        drivers[driver].delete(network_name)
        IPAM().release(network["IpRange"], network["IP"])
        Network.dump(default_network_path, network_name, None)

    @staticmethod
    def disconnect(container_info):
        # 清除 iptables 规则
        if container_info["PORTMAPPING"] is None:
            return
        for port_mapping in container_info["PORTMAPPING"]:
            host_port, container_port = port_mapping.split(":")
            endpoint_ip = container_info["IP"]
            command = f"iptables -t nat -D PREROUTING -p tcp -m tcp --dport {host_port} -j DNAT --to-destination {endpoint_ip}:{container_port}"
            shell(command)
