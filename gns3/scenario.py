import base64
import configparser
import hashlib
import ipaddress
import json
import os
import re
import resource
import time
import warnings

from collections import namedtuple
from telnetlib import Telnet
from typing import Any, List, Dict, Optional, Pattern

import requests

PROJECT_NAME = "iot_sim"

Server = namedtuple("Server", ("addr", "port", "auth", "user", "password"))
Project = namedtuple("Project", ("name", "id", "grid_unit"))
Item = namedtuple("Item", ("name", "id"))
Position = namedtuple("Position", ("x", "y"))


def md5sum_file(fname: str) -> str:
    """Get file MD5 checksum."""
    # TODO update in chunks.
    with open(fname, "rb") as f:
        data = f.read()
    return hashlib.md5(data).hexdigest()


def check_resources() -> None:
    """Check some system resources."""
    nofile_soft, nofile_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if nofile_soft <= 1024:
        msg = (
            f"The maximum number of open file descriptors for the current process is set to {nofile_soft}.\n"
            "This limit might not be enough to run multiple devices in GNS3 (approx more than 150 docker devices, may vary).\n"
            "To increase the limit, edit '/etc/security/limits.conf' and append: \n"
            "*                hard    nofile          65536\n"
            "*                soft    nofile          65536\n"
        )
        warnings.warn(msg, RuntimeWarning)


def check_local_gns3_config() -> bool:
    """Checks for the GNS3 server config."""
    config = configparser.ConfigParser()
    with open(os.path.expanduser("~/.config/GNS3/2.2/gns3_server.conf")) as f:
        config.read_file(f)
    if not "Qemu" in config.keys():
        warnings.warn("Qemu settings are not configured. Enable KVM for better performance.", RuntimeWarning)
        return False
    kvm = config["Qemu"].get("enable_kvm")
    if kvm is None:
        warnings.warn("'enable_kvm' key not defined. Enable KVM for better performance.", RuntimeWarning)
        return False
    if kvm == "false":
        warnings.warn("'enable_kvm' set to false. Enable KVM for better performance.", RuntimeWarning)
        return False
    print(f"KVM is set to {kvm}")
    return True


def read_local_gns3_config():
    """Return some GNS3 configuration values."""
    config = configparser.ConfigParser()
    with open(os.path.expanduser("~/.config/GNS3/2.2/gns3_server.conf")) as f:
        config.read_file(f)
    return config["Server"].get("host"), config["Server"].getint("port"), config["Server"].getboolean("auth"), config["Server"].get("user"), config["Server"].get("password")


def get_static_interface_config_file(iface: str, address: str, netmask: str, gateway: str, nameserver: Optional[str]) -> str:
    """Configuration file for a static network interface."""
    if nameserver is None:
        nameserver = gateway
    return (
        "# autogenerated\n"
        f"# Static config for {iface}\n"
        f"auto {iface}\n"
        f"iface {iface} inet static\n"
        f"\taddress {address}\n"
        f"\tnetmask {netmask}\n"
        f"\tgateway {gateway}\n"
        f"\tup echo nameserver {nameserver} > /etc/resolv.conf\n"
    )


def template_id_from_name(template: List[Dict[str, Any]], name: str) -> Optional[str]:
    """Get GNS3 template ID from the template name."""
    for d in template:
        if d["name"] == name:
            return d["template_id"]
    return None


def get_nodes_id_by_name_regexp(server: Server, project: Project, name_regexp: Pattern) -> Optional[List[Item]]:
    """Get the list of all node IDs that match a node name regular expression."""
    r = requests.get(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/nodes", auth=(server.user, server.password))
    r.raise_for_status()
    nodes: List[Dict[str, Any]] = r.json()
    nodes_filtered = list(filter(lambda n: name_regexp.match(n["name"]), nodes))
    return [Item(n["name"], n["node_id"]) for n in nodes_filtered]


def get_node_telnet_host_port(server: Server, project: Project, node_id: str) -> tuple:
    """Get the telnet hostname and port of a node."""
    r = requests.get(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/nodes/{node_id}", auth=(server.user, server.password))
    r.raise_for_status()
    # TODO include checks for console type
    assert r.json()["console_type"] == "telnet"
    if r.json()["console_host"] in ("0.0.0.0", "::"):
        host = server.addr
    else:
        host = r.json()["console_host"]
    return (host, r.json()["console"])


def get_links_id_from_node_connected_to_name_regexp(server: Server, project: Project, node_id: str, name_regexp: Pattern) -> Optional[List[Item]]:
    """Get all the link IDs from node node_id connected to other nodes with names that match name_regexp regular expression."""
    r = requests.get(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/nodes/{node_id}", auth=(server.user, server.password))
    r.raise_for_status()
    node_name = r.json()["name"]

    r = requests.get(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/nodes/{node_id}/links", auth=(server.user, server.password))
    r.raise_for_status()
    links = r.json()
    relevant_nodes = get_nodes_id_by_name_regexp(server, project, name_regexp)

    def is_link_relevant(link: Dict) -> Optional[Item]:
        for c in link["nodes"]: # two ends of the link
            for rn in relevant_nodes:
                if c["node_id"] == rn.id:
                    return rn
        return None

    links_filtered: List[Item]= []
    for link in links:
        linked_node = is_link_relevant(link)
        if linked_node:
            links_filtered.append(Item(f"{linked_node.name} <--> {node_name}", link["link_id"]))

    return links_filtered


def create_node(server: Server, project: Project, start_x: int, start_y: int, node_template_id: str, node_name: Optional[str] = None):
    """Create selected node at coordinates start_x, start_y."""
    payload = {"x": start_x, "y": start_y}
    if node_name:
        # GNS3 is not updating the name...
        payload["name"] = node_name
    r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/templates/{node_template_id}", data=json.dumps(payload), auth=(server.user, server.password))
    r.raise_for_status()
    return r.json()


def start_node(server: Server, project: Project, node_id: str) -> None:
    """Start selected node."""
    r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/nodes/{node_id}/start", data={}, auth=(server.user, server.password))
    r.raise_for_status()


def stop_node(server: Server, project: Project, node_id: str) -> None:
    """Stop selected node."""
    r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/nodes/{node_id}/stop", data={}, auth=(server.user, server.password))
    r.raise_for_status()


def delete_node(server: Server, project: Project, node_id: str) -> None:
    """Delete selected node."""
    # check if node is running?
    r = requests.delete(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/nodes/{node_id}", auth=(server.user, server.password))
    r.raise_for_status()


def create_link(server: Server, project: Project, node1_id: str, node1_port: int, node2_id: str, node2_port: int):
    """Create link between two nodes."""
    payload = {"nodes":[{"node_id": node1_id, "adapter_number": node1_port, "port_number": 0},
                        {"node_id": node2_id, "adapter_number": node2_port, "port_number": 0}]}
    r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/links", data=json.dumps(payload), auth=(server.user, server.password))
    r.raise_for_status()
    # TODO rename link node labels
    return r.json()


def create_cluster_of_devices(server, project, num_devices, start_x, start_y, switch_template_id, device_template_id, start_ip, devices_per_row=10):
    assert num_devices < 64  # parece que el switch por defecto no puede tener mas de 64 interfaces activas. Error while creating link: Dynamips error when running command ...
    # create cluster switch
    payload = {"x": start_x + int(devices_per_row/2)*project.grid_unit, "y": start_y - project.grid_unit}
    Xi, Yi = start_x, start_y # - project.grid_unit
    r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/templates/{switch_template_id}", data=json.dumps(payload), auth=(server.user, server.password))
    r.raise_for_status()
    switch_node_id = r.json()["node_id"]
    time.sleep(0.3)

    # create device grid
    devices_node_id = []
    dy = 0
    for i in range(num_devices):
        payload = {"x": start_x + (i%devices_per_row)*project.grid_unit, "y": start_y + dy}
        r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/templates/{device_template_id}", data=json.dumps(payload), auth=(server.user, server.password))
        r.raise_for_status()
        devices_node_id.append(r.json()["node_id"])
        if i%devices_per_row == devices_per_row-1:
            dy += project.grid_unit
        time.sleep(0.3)
    assert len(devices_node_id) == num_devices
    Xf, Yf = start_x + (devices_per_row-1)*project.grid_unit, start_y+dy
    # link devices to the switch
    devices_link_id = []
    for i, dev in enumerate(devices_node_id, start=1):
        # [!] for "Ethernet switch" (builtin) "adapter_number": 0, "port_number": i
        # ^_  https://docs.gns3.com/docs/using-gns3/beginners/switching-and-gns3/
        # [!] for Open vSwitch "adapter_number": i, "port_number": 0
        # for i in $(seq 16 63); do ovs-vsctl add-port br0 eth$i; done
        payload = {"nodes": [{"adapter_number": 0, "node_id": dev, "port_number": 0},
                             {"adapter_number": i, "node_id": switch_node_id, "port_number": 0}]}
        r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/links", data=json.dumps(payload), auth=(server.user, server.password))
        r.raise_for_status()
        devices_link_id.append(r.json()["link_id"])
        time.sleep(0.3)
    assert len(devices_link_id) == num_devices

    # change device configuration
    netmask = "255.255.0.0"
    for i, dev in enumerate(devices_node_id, start=0):
        payload = get_static_interface_config_file("eth0", start_ip+i, netmask, "192.168.0.1")
        r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/nodes/{dev}/files/etc/network/interfaces", data=payload, auth=(server.user, server.password))
        r.raise_for_status()
        print("Configured ", dev, " ", r.status_code)
        time.sleep(0.3)

    # decoration
    payload = {"x": start_x + (int(devices_per_row/2)+2)*project.grid_unit, "y": start_y - project.grid_unit,
               "svg": f"<svg><text>{start_ip}\n{start_ip+num_devices-1}\n{netmask}</text></svg>"}
    r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/drawings", data=json.dumps(payload), auth=(server.user, server.password))
    r.raise_for_status()

    return {"switch_node_id": switch_node_id, "devices_node_id": devices_node_id, "devices_link_id": devices_link_id}, (Xi, Yi, Xf, Yf)


def start_capture(server, project, link_ids):
    """Start packet capture (wireshark) in the selected link_ids."""
    for link in link_ids:
        r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/links/{link}/start_capture", data={}, auth=(server.user, server.password))
        r.raise_for_status()
        result = r.json()
        print(f"Capturing {result['capturing']}, {result['capture_file_name']}")
        time.sleep(0.3)


def stop_capture(server, project, link_ids):
    """Stop packet capture in the selected link_ids."""
    for link in link_ids:
        r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/links/{link}/stop_capture", data={}, auth=(server.user, server.password))
        r.raise_for_status()
        result = r.json()
        print(f"Capturing {result['capturing']}, {result['capture_file_name']}")
        time.sleep(0.3)


def start_all_switches(server: Server, project: Project, switches_pattern : Pattern=re.compile("openvswitch.*", re.IGNORECASE)) -> None:
    """Start all network switch nodes (OpenvSwitch switches)."""
    switches = get_nodes_id_by_name_regexp(server, project, switches_pattern)
    if switches:
        print(f"found {len(switches)} switches")
        for sw in switches:
            print(f"Starting {sw.name}... ", end="", flush=True)
            start_node(server, project, sw.id)
            print("OK")
            time.sleep(0.3)


def start_all_routers(server: Server, project: Project, routers_pattern : Pattern=re.compile("vyos.*", re.IGNORECASE)) -> None:
    """Start all router nodes (VyOS routers)."""
    routers = get_nodes_id_by_name_regexp(server, project, routers_pattern)
    if routers:
        print(f"found {len(routers)} routers")
        for r in routers:
            print(f"Starting {r.name}... ", end="", flush=True)
            start_node(server, project, r.id)
            print("OK")
            time.sleep(0.3)


def stop_all_switches(server: Server, project: Project, switches_pattern : Pattern=re.compile("openvswitch.*", re.IGNORECASE)) -> None:
    """Stop all network switch nodes (OpenvSwitch switches)."""
    switches = get_nodes_id_by_name_regexp(server, project, switches_pattern)
    if switches:
        print(f"found {len(switches)} switches")
        for sw in switches:
            print(f"Stopping {sw.name}... ", end="", flush=True)
            stop_node(server, project, sw.id)
            print("OK")
            time.sleep(0.3)


def stop_all_routers(server: Server, project: Project, routers_pattern : Pattern=re.compile("vyos.*", re.IGNORECASE)) -> None:
    """Stop all router nodes (VyOS routers)."""
    routers = get_nodes_id_by_name_regexp(server, project, routers_pattern)
    if routers:
        print(f"found {len(routers)} routers")
        for r in routers:
            print(f"Stopping {r.name}... ", end="", flush=True)
            stop_node(server, project, r.id)
            print("OK")
            time.sleep(0.3)


def start_capture_all_iot_links(server, project, switches_pattern: Pattern=re.compile("openvswitch.*", re.IGNORECASE), iot_pattern: Pattern=re.compile("mqtt-device.*|coap-device.*", re.IGNORECASE)) -> None:
    """Start packet capture on each IoT device."""
    switches = get_nodes_id_by_name_regexp(server, project, switches_pattern)
    if switches:
        print(f"found {len(switches)} switches")
        for sw in switches:
            print(f"Finding links in switch {sw.name}... ", end="", flush=True)
            links = get_links_id_from_node_connected_to_name_regexp(server, project, sw.id, iot_pattern)
            if links:
                print(f"{len(links)} found")
                for lk in links:
                    print(f"\t Starting capture in link {lk.name}... ", end="", flush=True)
                    start_capture(server, project, [lk.id])
                    print("OK")
            else:
                print("0 links, skipping.")
        time.sleep(0.3)


def stop_capture_all_iot_links(server, project, switches_pattern: Pattern=re.compile("openvswitch.*", re.IGNORECASE), iot_pattern: Pattern=re.compile("mqtt-device.*|coap-device.*", re.IGNORECASE)) -> None:
    """Stop packet capture on each IoT device."""
    switches = get_nodes_id_by_name_regexp(server, project, switches_pattern)
    if switches:
        print(f"found {len(switches)} switches")
        for sw in switches:
            print(f"Finding links in switch {sw.name}... ", end="", flush=True)
            links = get_links_id_from_node_connected_to_name_regexp(server, project, sw.id, iot_pattern)
            if links:
                print(f"{len(links)} found")
                for lk in links:
                    print(f"\t Stopping capture in link {lk.name}... ", end="", flush=True)
                    stop_capture(server, project, [lk.id])
                    print("OK")
            else:
                print("0 links, skipping.")
        time.sleep(0.3)


def install_vyos_image_on_node(node_id: str, hostname: str, telnet_port: int) -> None:
    """Perform VyOS installation steps."""
    with Telnet(hostname, telnet_port) as tn:
        out = tn.read_until(b"vyos login:")
        print(out.decode("utf-8").split("\n")[-1])

        tn.write(b"vyos\n")
        out = tn.expect([b"Password:"], timeout=10)
        print(out[2].decode("utf-8"))

        tn.write(b"vyos\n")
        out = tn.expect([b"vyos@vyos:~\$"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"install image\n")
        out = tn.expect([b"Would you like to continue\? \(Yes/No\)"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"Yes\n")
        out = tn.expect([b"Partition \(Auto/Parted/Skip\)"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"Auto\n")
        out = tn.expect([b"Install the image on"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"\n")
        out = tn.expect([b"Continue\? \(Yes/No\)"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"Yes\n")
        out = tn.expect([b"How big of a root partition should I create"], timeout=30)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"\n")
        out = tn.expect([b"What would you like to name this image"], timeout=30)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"\n")
        out = tn.expect([b"Which one should I copy to"], timeout=30)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"\n")
        out = tn.expect([b"Enter password for user 'vyos':"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"vyos\n")
        out = tn.expect([b"Retype password for user 'vyos':"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"vyos\n")
        out = tn.expect([b"Which drive should GRUB modify the boot partition on"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"\n")
        out = tn.expect([b"vyos@vyos:~\$"], timeout=30)
        print(out[0])
        print(out[2].decode("utf-8"))

        time.sleep(2)
        tn.write(b"poweroff\n")
        out = tn.expect([b"Are you sure you want to poweroff this system"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"y\n")
        time.sleep(2)


def configure_vyos_image_on_node(node_id: str, hostname: str, telnet_port: int, path_script: str) -> None:
    """Configure VyOS router."""
    local_checksum = md5sum_file(path_script)

    with open(path_script, "rb") as f:
        config = base64.b64encode(f.read())

    with Telnet(hostname, telnet_port) as tn:
        out = tn.read_until(b"vyos login:")
        print(out.decode("utf-8").split("\n")[-1])

        tn.write(b"vyos\n")
        out = tn.expect([b"Password:"], timeout=10)
        print(out[2].decode("utf-8"))

        tn.write(b"vyos\n")
        out = tn.expect([b"vyos@vyos:~\$"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        payload = b"echo '" + config + b"' >> config.b64\n"
        tn.write(payload)
        out = tn.expect([b"vyos@vyos:~\$"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"base64 --decode config.b64 > config.sh\n")
        out = tn.expect([b"vyos@vyos:~\$"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"md5sum config.sh\n")
        out = tn.expect([re.compile(r"[0-9a-f]{32}  config.sh".encode("utf-8"))], 5)
        if out[0] == -1:
            warnings.warn("Error generating file MD5 checksum.", RuntimeWarning)
            return
        uploaded_checksum = out[1].group().decode("utf-8").split()[0]

        if uploaded_checksum != local_checksum:
            warnings.warn("Checksums do not match.", RuntimeWarning)
        else:
            print("Checksums match.")

        tn.write(b"chmod +x config.sh\n")
        out = tn.expect([b"vyos@vyos:~\$"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"./config.sh\n")
        out = tn.expect([b"Done"], timeout=60)
        print(out[0])
        print(out[2].decode("utf-8"))
        out = tn.expect([b"vyos@vyos:~\$"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"poweroff\n")
        out = tn.expect([b"Are you sure you want to poweroff this system"], timeout=10)
        print(out[0])
        print(out[2].decode("utf-8"))

        tn.write(b"y\n")
        time.sleep(2)


check_resources()
check_local_gns3_config()
server = Server(*read_local_gns3_config())

req_version = requests.get(f"http://{server.addr}:{server.port}/v2/version", auth=(server.user, server.password))
req_version.raise_for_status()
print(req_version.json())

req_projects = requests.get(f"http://{server.addr}:{server.port}/v2/projects", auth=(server.user, server.password))
req_projects.raise_for_status()
projects: List[Dict[str, Any]] = req_projects.json()
print(len(projects), " projects")
if projects:
    for p in projects:
        print(f"Name='{p['name']}', ID='{p['project_id']}'")

filtered_projects = list(filter(lambda x: x["name"]==PROJECT_NAME, projects))
if filtered_projects:
    p = filtered_projects[0]
    project = Project(name=p["name"], id=p["project_id"], grid_unit=int(p["grid_size"]*1.4))
    print(f"Project {PROJECT_NAME} exists. ", project)
else:
    # create the project
    # http://api.gns3.net/en/2.2/api/v2/controller/project/projects.html
    # Coordinate 0,0 is located in the center of the project
    payload_project = {"name": PROJECT_NAME, "show_grid": True, "scene_height": 2000, "scene_width": 4000}
    r = requests.post(f"http://{server.addr}:{server.port}/v2/projects", data=json.dumps(payload_project), auth=(server.user, server.password))
    r.raise_for_status()
    p = r.json()
    project = Project(name=p["name"], id=p["project_id"], grid_unit=int(p["grid_size"]*1.4))
    assert project.name == PROJECT_NAME
    print("Created project ", project)

# open project if closed
if p["status"] == "closed":
    r = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/open", data={}, auth=(server.user, server.password))
    r.raise_for_status()
    assert r.json()["status"] == "opened"

# Por ahora crear los templates en GNS3 GUI
# get templates
r = requests.get(f"http://{server.addr}:{server.port}/v2/templates", auth=(server.user, server.password))
r.raise_for_status()
templates = r.json()

# get template ids
router_template_id = template_id_from_name(templates, "VyOS 1.3.0")
assert router_template_id
switch_template_id = template_id_from_name(templates, "Open vSwitch")
assert switch_template_id

mqtt_device_t1_template_id = template_id_from_name(templates, "mqtt-device-t1")
assert mqtt_device_t1_template_id
mqtt_device_t2_template_id = template_id_from_name(templates, "mqtt-device-t2")
assert mqtt_device_t2_template_id
coap_device_t1_template_id = template_id_from_name(templates, "coap-device-t1")
assert coap_device_t1_template_id

############
# TOPOLOGY #
############

coord_rnorth = Position(0, -300)
coord_rwest = Position(-150, -75)
coord_reast = Position(150, -75)

# routers
rnorth = create_node(server, project, coord_rnorth.x, coord_rnorth.y, router_template_id)
rwest = create_node(server, project, coord_rwest.x, coord_rwest.y, router_template_id)
reast = create_node(server, project, coord_reast.x, coord_reast.y, router_template_id)

create_link(server, project, rnorth["node_id"], 1, rwest["node_id"], 1)
create_link(server, project, rnorth["node_id"], 2, reast["node_id"], 1)
create_link(server, project, rwest["node_id"], 2, reast["node_id"], 2)

# switches
coord_snorth = Position(coord_rnorth.x, coord_rnorth.y - 150)
coord_swest = Position(coord_rwest.x - 300, coord_rwest.y)
coord_seast = Position(coord_reast.x + 300, coord_reast.y)

snorth = create_node(server, project, coord_snorth.x, coord_snorth.y, switch_template_id)
swest = create_node(server, project, coord_swest.x, coord_swest.y, switch_template_id)
seast = create_node(server, project, coord_seast.x, coord_seast.y, switch_template_id)

create_link(server, project, rnorth["node_id"], 0, snorth["node_id"], 0)
create_link(server, project, rwest["node_id"], 0, swest["node_id"], 0)
create_link(server, project, reast["node_id"], 0, seast["node_id"], 0)

# routers west zone
routers_west_zone = []
coords_west_zone = []
swest_freeport = 1
for i in [-3, -1, 1, 3]:
    coord_rwz = Position(coord_swest.x + 150*i, coord_swest.y + 150)
    rwz = create_node(server, project, coord_rwz.x, coord_rwz.y, router_template_id)
    create_link(server, project, rwz["node_id"], 1, swest["node_id"], swest_freeport)
    swest_freeport += 1
    swz = create_node(server, project, coord_rwz.x, coord_rwz.y + 150, switch_template_id)
    create_link(server, project, rwz["node_id"], 0, swz["node_id"], 0)
    routers_west_zone.append(rwz)
    coords_west_zone.append(coord_rwz)

# routers east zone
routers_east_zone = []
coords_east_zone = []
seast_freeport = 1
for i in [-2, 0, 2]:
    coord_rez = Position(coord_seast.x + 150*i, coord_seast.y + 150)
    rez = create_node(server, project, coord_rez.x, coord_rez.y, router_template_id)
    create_link(server, project, rez["node_id"], 1, seast["node_id"], seast_freeport)
    seast_freeport += 1
    sez = create_node(server, project, coord_rez.x, coord_rez.y + 150, switch_template_id)
    create_link(server, project, rez["node_id"], 0, sez["node_id"], 0)
    routers_east_zone.append(rez)
    coords_east_zone.append(coord_rez)

# -1900, -400

cluster_mqtt1, coord = create_cluster_of_devices(server, project, 50, -1900, -300, switch_template_id, mqtt_device_t1_template_id, ipaddress.IPv4Address("192.168.10.1"))
cluster_mqtt2, coord = create_cluster_of_devices(server, project, 50, coord[2]+2*project.grid_unit, coord[1], switch_template_id, mqtt_device_t2_template_id, ipaddress.IPv4Address("192.168.20.1"))
cluster_coap1, coord = create_cluster_of_devices(server, project, 50, coord[2]+2*project.grid_unit, coord[1], switch_template_id, coap_device_t1_template_id, ipaddress.IPv4Address("192.168.30.1"))

start_capture(server, project, cluster_mqtt1["devices_link_id"])
start_capture(server, project, cluster_mqtt2["devices_link_id"])
start_capture(server, project, cluster_coap1["devices_link_id"])

# get_nodes_id_by_name_regexp(server, project, re.compile("openvswitch.*", re.IGNORECASE))
# get_links_id_from_node_connected_to_name_regexp(server, project, '4a2a6591-7b87-4c8d-948f-50eed4cd2c61', re.compile("mqtt-device-t1.*", re.IGNORECASE))

# --------------------------------------------
# start_all_switches(server, project)
# click play button in GNS3 |>
# check coap cloud
# start_capture_all_iot_links(server, project)
# stop_capture_all_iot_links(server, project)
