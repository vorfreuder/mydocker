import subprocess
import sys

from utility import shell


class BridgeNetworkDriver:
    name = "bridge"

    @staticmethod
    # 创建 Bridge 设备
    def create(subnet, ip, name):
        # 1）创建 Bridge 虚拟设备
        command = f"ip link add {name} type bridge"
        shell(command)
        # 2）设置 Bridge 设备地址和路由
        command = f"ip addr add {ip} dev {name}"
        shell(command)
        # 3）启动 Bridge 设备
        command = f"ip link set dev {name} up"
        shell(command)
        # 4）设置 iptables SNAT 规则
        command = "sysctl -w net.ipv4.ip_forward=1"
        shell(command)
        command = (
            f"iptables -t nat -A POSTROUTING -s {subnet} ! -o {name} -j MASQUERADE"
        )
        shell(command)

    @staticmethod
    # 删除 Bridge 设备
    def delete(name):
        command = f"ip link delete dev {name}"
        shell(command, exit_if_error=False)

    @staticmethod
    # 将 veth 关联到网桥
    def connect(network, endpoint):
        bridge_name = network["NAME"]
        # 创建 Veth 接口
        veth_name = endpoint["ID"][:5]
        peer_veth_name = "cif-" + veth_name
        command = f"ip link add {veth_name} type veth peer name {peer_veth_name}"
        endpoint["PEERNAME"] = peer_veth_name
        shell(command)
        # 将 Veth 接口挂载到 Bridge 设备
        command = f"ip link set {veth_name} master {bridge_name}"
        shell(command)
        # 启动 Veth
        command = f"ip link set dev {veth_name} up"
        shell(command)

    @staticmethod
    # 将 veth 从网桥解绑
    def disconnect(network, endpoint):
        veth_name = endpoint["ID"][:5]
        # 从 Bridge 设备解绑 Veth 接口
        command = f"ip link set {veth_name} nomaster"
        shell(command)
        # 删除 Veth 接口
        command = f"ip link delete dev {veth_name}"
        shell(command)


if __name__ == "__main__":
    bridge_name = "testbridge"
    BridgeNetworkDriver.create("10.0.0.0/24", "10.0.0.1", bridge_name)
    network = {"NAME": bridge_name}
    endpoint = {"ID": "testcontainer"}
    BridgeNetworkDriver.connect(network, endpoint)
    print(endpoint)
    BridgeNetworkDriver.disconnect(network, endpoint)
    BridgeNetworkDriver.delete(bridge_name)
