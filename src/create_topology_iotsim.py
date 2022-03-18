"""Create iot simulation topology (simple)."""

import configparser
import ipaddress
import sys
import time

from gns3utils import *

PROJECT_NAME = "iot_sim"
AUTO_CONFIGURE_ROUTERS = True

check_resources()
check_local_gns3_config()
server = Server(*read_local_gns3_config())

check_server_version(server)

project = get_project_by_name(server, PROJECT_NAME)

if project:
    print(f"Project {PROJECT_NAME} exists. ", project)
else:
    project = create_project(server, PROJECT_NAME, 5000, 7500, 15)
    print("Created project ", project)

open_project_if_closed(server, project)

if len(get_all_nodes(server, project)) > 0:
    print("Project is not empty!")
    sys.exit(1)

# Create the templates manually using the GNS3 GUI
# get templates
templates = get_all_templates(server)

# get template ids
router_template_id = get_template_id_from_name(templates, "VyOS 1.3.0")
assert router_template_id
switch_template_id = get_template_id_from_name(templates, "Open vSwitch")
assert switch_template_id

DNS_template_id = get_template_id_from_name(templates, "iotsim-dns")
assert DNS_template_id
certificates_template_id = get_template_id_from_name(templates, "iotsim-certificates")
assert certificates_template_id
NTP_template_id = get_template_id_from_name(templates, "iotsim-ntp")
assert NTP_template_id
Merlin_template_id = get_template_id_from_name(templates, "iotsim-merlin-cnc")
assert Merlin_template_id
Mirai_builder_template_id = get_template_id_from_name(templates, "iotsim-mirai-builder")
assert Mirai_builder_template_id
Mirai_cnc_template_id = get_template_id_from_name(templates, "iotsim-mirai-cnc")
assert Mirai_cnc_template_id
Mirai_bot_template_id = get_template_id_from_name(templates, "iotsim-mirai-bot")
assert Mirai_bot_template_id
Mirai_scan_listener_template_id = get_template_id_from_name(templates, "iotsim-mirai-scan-listener")
assert Mirai_scan_listener_template_id
Mirai_loader_template_id = get_template_id_from_name(templates, "iotsim-mirai-loader")
assert Mirai_loader_template_id
Mirai_wget_loader_template_id = get_template_id_from_name(templates, "iotsim-mirai-wget-loader")
assert Mirai_wget_loader_template_id
mqtt_broker_1_6_template_id = get_template_id_from_name(templates, "iotsim-mqtt-broker-1.6")
assert mqtt_broker_1_6_template_id
mqtt_broker_tls_template_id = get_template_id_from_name(templates, "iotsim-mqtt-broker-tls")
assert mqtt_broker_tls_template_id
mqtt_client_t1_template_id = get_template_id_from_name(templates, "iotsim-mqtt-client-t1")
assert mqtt_client_t1_template_id
mqtt_client_t2_template_id = get_template_id_from_name(templates, "iotsim-mqtt-client-t2")
assert mqtt_client_t2_template_id
air_quality_template_id = get_template_id_from_name(templates, "iotsim-air-quality")
assert air_quality_template_id
cooler_motor_template_id = get_template_id_from_name(templates, "iotsim-cooler-motor")
assert cooler_motor_template_id
predictive_maintenance_template_id = get_template_id_from_name(templates, "iotsim-predictive-maintenance")
assert predictive_maintenance_template_id
hydraulic_system_template_id = get_template_id_from_name(templates, "iotsim-hydraulic-system")
assert hydraulic_system_template_id
building_monitor_template_id = get_template_id_from_name(templates, "iotsim-building-monitor")
assert building_monitor_template_id
domotic_monitor_template_id = get_template_id_from_name(templates, "iotsim-domotic-monitor")
assert domotic_monitor_template_id
coap_server_template_id = get_template_id_from_name(templates, "iotsim-coap-server")
assert coap_server_template_id
coap_cloud_template_id = get_template_id_from_name(templates, "iotsim-coap-cloud")
assert coap_cloud_template_id
city_power_template_id = get_template_id_from_name(templates, "iotsim-city-power")
assert city_power_template_id
city_power_tls_template_id = get_template_id_from_name(templates, "iotsim-city-power-tls")
assert city_power_tls_template_id
combined_cycle_template_id = get_template_id_from_name(templates, "iotsim-combined-cycle")
assert combined_cycle_template_id
combined_cycle_tls_template_id = get_template_id_from_name(templates, "iotsim-combined-cycle-tls")
assert combined_cycle_tls_template_id
city_power_cloud_template_id = get_template_id_from_name(templates, "iotsim-city-power-cloud")
assert city_power_cloud_template_id
combined_cycle_cloud_template_id = get_template_id_from_name(templates, "iotsim-combined-cycle-cloud")
assert combined_cycle_cloud_template_id
ip_camera_street_template_id = get_template_id_from_name(templates, "iotsim-ip-camera-street")
assert ip_camera_street_template_id
ip_camera_museum_template_id = get_template_id_from_name(templates, "iotsim-ip-camera-museum")
assert ip_camera_museum_template_id
stream_server_template_id = get_template_id_from_name(templates, "iotsim-stream-server")
assert stream_server_template_id
stream_consumer_template_id = get_template_id_from_name(templates, "iotsim-stream-consumer")
assert stream_consumer_template_id
debug_client_template_id = get_template_id_from_name(templates, "iotsim-debug-client")
assert debug_client_template_id
mqtt_client_t1_compromised_template_id = get_template_id_from_name(templates, "iotsim-mqtt-client-compromised-t1")
assert mqtt_client_t1_compromised_template_id
mqtt_client_t2_compromised_template_id = get_template_id_from_name(templates, "iotsim-mqtt-client-compromised-t2")
assert mqtt_client_t2_compromised_template_id
coap_server_compromised_template_id = get_template_id_from_name(templates, "iotsim-coap-server-compromised")
assert coap_server_compromised_template_id


# read project configuration file
sim_config = configparser.ConfigParser()
with open("../iot-sim.config", "r", encoding="utf-8") as cf:
    # include fake section header 'main'
    sim_config.read_string(f"[main]\n{cf.read()}")
    sim_config = sim_config["main"]


input("Open the GNS3 project GUI. Press enter to continue...")

############
# TOPOLOGY #
############
# Coordinates:
#
#            ^
#  --        | Y -    +-
#            |
#            |
#  X -       |(0,0)   X +
# <----------+---------->
#            |
#            |
#            |
#            |
#  -+        v Y +     ++

coord_rnorth = Position(1000, -2000)
coord_rwest = Position(coord_rnorth.x - project.grid_unit * 2, coord_rnorth.y + project.grid_unit * 4)
coord_reast = Position(coord_rnorth.x + project.grid_unit * 2, coord_rnorth.y + project.grid_unit * 4)

# backbone routers
rnorth = create_node(server, project, coord_rnorth.x, coord_rnorth.y, router_template_id)
rwest = create_node(server, project, coord_rwest.x, coord_rwest.y, router_template_id)
reast = create_node(server, project, coord_reast.x, coord_reast.y, router_template_id)

create_link(server, project, rnorth["node_id"], 1, rwest["node_id"], 1)
create_link(server, project, rnorth["node_id"], 2, reast["node_id"], 1)
create_link(server, project, rwest["node_id"], 2, reast["node_id"], 2)

# router installation and configuration. TODO in parallel?
backbone_routers = [rnorth, rwest, reast]
backbone_configs = ["../router/backbone/router_north.sh",
                    "../router/backbone/router_west.sh",
                    "../router/backbone/router_east.sh"]
if AUTO_CONFIGURE_ROUTERS:
    for router_node, router_config in zip(backbone_routers, backbone_configs):
        print(f"Installing {router_node['name']}")
        hostname, port = get_node_telnet_host_port(server, project, router_node["node_id"])
        terminal_cmd = f"konsole -e telnet {hostname} {port}"
        start_node(server, project, router_node["node_id"])
        install_vyos_image_on_node(router_node["node_id"], hostname, port, pre_exec=terminal_cmd)
        # time to close the terminals, else Telnet throws EOF errors
        time.sleep(10)
        print(f"Configuring {router_node['name']} with {router_config}")
        start_node(server, project, router_node["node_id"])
        configure_vyos_image_on_node(router_node["node_id"], hostname, port, router_config, pre_exec=terminal_cmd)
        time.sleep(10)

# backbone switches
coord_snorth = Position(coord_rnorth.x, coord_rnorth.y - project.grid_unit * 2)
coord_swest = Position(coord_rwest.x - project.grid_unit * 10, coord_rwest.y)
coord_seast = Position(coord_reast.x + project.grid_unit * 25, coord_reast.y)

snorth = create_node(server, project, coord_snorth.x, coord_snorth.y, switch_template_id)
swest = create_node(server, project, coord_swest.x, coord_swest.y, switch_template_id)
seast = create_node(server, project, coord_seast.x, coord_seast.y, switch_template_id)

create_link(server, project, rnorth["node_id"], 0, snorth["node_id"], 0)
create_link(server, project, rwest["node_id"], 0, swest["node_id"], 0)
create_link(server, project, reast["node_id"], 0, seast["node_id"], 0)

# west zone routers and switches
routers_west_zone = []
switches_west_zone = []
coords_west_zone = []
switch_freeport = 1
for i in [-40, -20, 0, 20]:
    coord = Position(coord_swest.x + project.grid_unit * i, coord_swest.y + project.grid_unit * 3)
    rzone = create_node(server, project, coord.x, coord.y, router_template_id)
    create_link(server, project, rzone["node_id"], 1, swest["node_id"], switch_freeport)
    switch_freeport += 1
    coord = Position(coord.x, coord.y + project.grid_unit * 2)
    szone = create_node(server, project, coord.x, coord.y, switch_template_id)
    create_link(server, project, rzone["node_id"], 0, szone["node_id"], 0)
    routers_west_zone.append(rzone)
    switches_west_zone.append(szone)
    coords_west_zone.append(coord)

# router installation and configuration
rwest_configs = [f"../router/locations/router_loc{i}.sh" for i in range(1, 5)]
if AUTO_CONFIGURE_ROUTERS:
    for router_node, router_config in zip(routers_west_zone, rwest_configs):
        print(f"Installing {router_node['name']}")
        hostname, port = get_node_telnet_host_port(server, project, router_node["node_id"])
        terminal_cmd = f"konsole -e telnet {hostname} {port}"
        start_node(server, project, router_node["node_id"])
        install_vyos_image_on_node(router_node["node_id"], hostname, port, pre_exec=terminal_cmd)
        # time to close the terminals, else Telnet throws EOF errors
        time.sleep(10)
        print(f"Configuring {router_node['name']} with {router_config}")
        start_node(server, project, router_node["node_id"])
        configure_vyos_image_on_node(router_node["node_id"], hostname, port, router_config, pre_exec=terminal_cmd)
        time.sleep(10)

# east zone routers and switches
routers_east_zone = []
switches_east_zone = []
coords_east_zone = []
switch_freeport = 1
for i in [-5, 0, 5]:
    coord = Position(coord_seast.x + project.grid_unit * i, coord_seast.y + project.grid_unit * 3)
    rzone = create_node(server, project, coord.x, coord.y, router_template_id)
    create_link(server, project, rzone["node_id"], 1, seast["node_id"], switch_freeport)
    switch_freeport += 1
    coord = Position(coord.x, coord.y + project.grid_unit * 2)
    szone = create_node(server, project, coord.x, coord.y, switch_template_id)
    create_link(server, project, rzone["node_id"], 0, szone["node_id"], 0)
    routers_east_zone.append(rzone)
    switches_east_zone.append(szone)
    coords_east_zone.append(coord)

# router installation and configuration
reast_configs = [f"../router/locations/router_loc{i}.sh" for i in range(5, 8)]
if AUTO_CONFIGURE_ROUTERS:
    for router_node, router_config in zip(routers_east_zone, reast_configs):
        print(f"Installing {router_node['name']}")
        hostname, port = get_node_telnet_host_port(server, project, router_node["node_id"])
        terminal_cmd = f"konsole -e telnet {hostname} {port}"
        start_node(server, project, router_node["node_id"])
        install_vyos_image_on_node(router_node["node_id"], hostname, port, pre_exec=terminal_cmd)
        # time to close the terminals, else Telnet throws EOF errors
        time.sleep(10)
        print(f"Configuring {router_node['name']} with {router_config}")
        start_node(server, project, router_node["node_id"])
        configure_vyos_image_on_node(router_node["node_id"], hostname, port, router_config, pre_exec=terminal_cmd)
        time.sleep(10)


lab_nameserver = sim_config["LAB_DNS_IPADDR"]

# Mirai

mirai_cnc = create_node(server, project, coords_east_zone[0].x - project.grid_unit, coords_east_zone[0].y + project.grid_unit * 2, Mirai_cnc_template_id)
create_link(server, project, switches_east_zone[0]["node_id"], 1, mirai_cnc["node_id"], 0)
set_node_network_interfaces(server, project, mirai_cnc["node_id"], "eth0", ipaddress.IPv4Interface(f"{sim_config['MIRAI_CNC_IPADDR']}/24"), "192.168.33.1", lab_nameserver)

mirai_scan_listener = create_node(server, project, coords_east_zone[0].x + project.grid_unit, coords_east_zone[0].y + project.grid_unit * 2, Mirai_scan_listener_template_id)
create_link(server, project, switches_east_zone[0]["node_id"], 2, mirai_scan_listener["node_id"], 0)
set_node_network_interfaces(server, project, mirai_scan_listener["node_id"], "eth0", ipaddress.IPv4Interface(f"{sim_config['MIRAI_REPORT_IPADDR']}/24"), "192.168.33.1", lab_nameserver)

mirai_loader = create_node(server, project, coords_east_zone[0].x - project.grid_unit, coords_east_zone[0].y + project.grid_unit * 3, Mirai_loader_template_id)
create_link(server, project, switches_east_zone[0]["node_id"], 3, mirai_loader["node_id"], 0)
set_node_network_interfaces(server, project, mirai_loader["node_id"], "eth0", ipaddress.IPv4Interface("192.168.33.12/24"), "192.168.33.1", lab_nameserver)

mirai_wget_loader = create_node(server, project, coords_east_zone[0].x + project.grid_unit, coords_east_zone[0].y + project.grid_unit * 3, Mirai_wget_loader_template_id)
create_link(server, project, switches_east_zone[0]["node_id"], 4, mirai_wget_loader["node_id"], 0)
set_node_network_interfaces(server, project, mirai_wget_loader["node_id"], "eth0", ipaddress.IPv4Interface(f"{sim_config['MIRAI_WGET_LOADER_IPADDR']}/24"), "192.168.33.1", lab_nameserver)

mirai_bot = create_node(server, project, coord_snorth.x + project.grid_unit * 8, coord_snorth.y - project.grid_unit * 2, Mirai_bot_template_id)
create_link(server, project, snorth["node_id"], 1, mirai_bot["node_id"], 0)
set_node_network_interfaces(server, project, mirai_bot["node_id"], "eth0", ipaddress.IPv4Interface("192.168.0.100/20"), "192.168.0.1", lab_nameserver)

# Merlin

merlin_cnc = create_node(server, project, coords_east_zone[1].x, coords_east_zone[1].y + project.grid_unit * 2, Merlin_template_id)
create_link(server, project, switches_east_zone[1]["node_id"], 1, merlin_cnc["node_id"], 0)
set_node_network_interfaces(server, project, merlin_cnc["node_id"], "eth0", ipaddress.IPv4Interface("192.168.34.10/24"), "192.168.34.1", lab_nameserver)


# Scan
# TODO.

# DNS
dns = create_node(server, project, coord_snorth.x + project.grid_unit * 6, coord_snorth.y - project.grid_unit * 2, DNS_template_id)
create_link(server, project, snorth["node_id"], 2, dns["node_id"], 0)
set_node_network_interfaces(server, project, dns["node_id"], "eth0", ipaddress.IPv4Interface(f"{lab_nameserver}/20"), "192.168.0.1", "127.0.0.1")

# NTP

ntp = create_node(server, project, coord_snorth.x + project.grid_unit * 4, coord_snorth.y - project.grid_unit * 2, NTP_template_id)
create_link(server, project, snorth["node_id"], 3, ntp["node_id"], 0)
set_node_network_interfaces(server, project, ntp["node_id"], "eth0", ipaddress.IPv4Interface("192.168.0.3/20"), "192.168.0.1", lab_nameserver)


########## debug clients ##########
# d_n1 = create_node(server, project, coord_snorth.x, coord_snorth.y - project.grid_unit * 2, debug_template_id)
# d_w1 = create_node(server, project, coords_west_zone[0].x, coords_west_zone[0].y + project.grid_unit * 2, debug_template_id)
# d_w2 = create_node(server, project, coords_west_zone[1].x, coords_west_zone[1].y + project.grid_unit * 2, debug_template_id)
# d_w3 = create_node(server, project, coords_west_zone[2].x, coords_west_zone[2].y + project.grid_unit * 2, debug_template_id)
# d_w4 = create_node(server, project, coords_west_zone[3].x, coords_west_zone[3].y + project.grid_unit * 2, debug_template_id)
# d_e1 = create_node(server, project, coords_east_zone[0].x, coords_east_zone[0].y + project.grid_unit * 2, debug_template_id)
# d_e2 = create_node(server, project, coords_east_zone[1].x, coords_east_zone[1].y + project.grid_unit * 2, debug_template_id)
# d_e3 = create_node(server, project, coords_east_zone[2].x, coords_east_zone[2].y + project.grid_unit * 2, debug_template_id)

# create_link(server, project, snorth["node_id"], 1, d_n1["node_id"], 0)
# create_link(server, project, switches_west_zone[0]["node_id"], 1, d_w1["node_id"], 0)
# create_link(server, project, switches_west_zone[1]["node_id"], 1, d_w2["node_id"], 0)
# create_link(server, project, switches_west_zone[2]["node_id"], 1, d_w3["node_id"], 0)
# create_link(server, project, switches_west_zone[3]["node_id"], 1, d_w4["node_id"], 0)
# create_link(server, project, switches_east_zone[0]["node_id"], 1, d_e1["node_id"], 0)
# create_link(server, project, switches_east_zone[1]["node_id"], 1, d_e2["node_id"], 0)
# create_link(server, project, switches_east_zone[2]["node_id"], 1, d_e3["node_id"], 0)

# set_node_network_interfaces(server, project, d_n1["node_id"], "eth0", ipaddress.IPv4Interface("192.168.0.2/20"), "192.168.0.1")
# set_node_network_interfaces(server, project, d_w1["node_id"], "eth0", ipaddress.IPv4Interface("192.168.17.10/24"), "192.168.17.1")
# set_node_network_interfaces(server, project, d_w2["node_id"], "eth0", ipaddress.IPv4Interface("192.168.18.10/24"), "192.168.18.1")
# set_node_network_interfaces(server, project, d_w3["node_id"], "eth0", ipaddress.IPv4Interface("192.168.19.10/24"), "192.168.19.1")
# set_node_network_interfaces(server, project, d_w4["node_id"], "eth0", ipaddress.IPv4Interface("192.168.20.10/24"), "192.168.20.1")
# set_node_network_interfaces(server, project, d_e1["node_id"], "eth0", ipaddress.IPv4Interface("192.168.33.10/24"), "192.168.33.1")
# set_node_network_interfaces(server, project, d_e2["node_id"], "eth0", ipaddress.IPv4Interface("192.168.34.10/24"), "192.168.34.1")
# set_node_network_interfaces(server, project, d_e3["node_id"], "eth0", ipaddress.IPv4Interface("192.168.35.10/24"), "192.168.35.1")
