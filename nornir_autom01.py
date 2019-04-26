#!/usr/bin/env python

from nornir import InitNornir
from nornir.plugins.functions.text import print_title, print_result
from nornir.plugins.tasks.data import load_yaml
from nornir.plugins.tasks import networking, text
from nornir.core.filter import F
import yaml
import sys
import os
import os.path

nr = InitNornir(config_file="nornir_config.yaml")
dir_fact = "./FACTS"
dir_config = "./CONFIG"
dir_backup = "./BACKUP"
dir_template = "./templates"
extra_vars = "./EXTRAS"

def trash():
    print(nr.inventory.hosts)
    #Complex Filter by groups and return all host
    group01 = nr.filter(F(groups__contains="distribution-switch"))
    print(group01.inventory.hosts)

    #Filter by platerform and return
    cisco = nr.filter(F(platform="cisco-ios"))
    print(cisco.inventory.hosts)

    #Access Nested Data
    nested_str = nr.filter(F(nested_data__a_string__contains="intf"))
    print(nested_str.inventory.hosts.keys())

    result = nr.filter(site="VICTORIA", role="test-device")
    print(result.inventory.hosts)

    # print_result(result)
    # print(nr.inventory.hosts['CSR1000v-lab'].keys())
    # print(nr.inventory.hosts['CSR1000v-lab']['facts']['facts']['interface_list'])

def get_host_fact(task):
    get_fact = task.run(task=networking.napalm_get, getters=['facts'])
    #Keep fact on host variable
    task.host['facts'] = get_fact.result
    #Keep fact on FACT FOLDER
    savetodir(convertoyaml(get_fact.result), dir_fact, task.host)
def get_backup(task):
    show_command_lst = [
        'terminal length 0',
        'show running-config'
    ]
    result = task.run(
        task=networking.netmiko_send_command,
        command_string=show_command_lst[1],
    )
    output = result[0].result

    #result = task.run(task=networking.netmiko_send_command(sh_command))
    savetodir(output, dir_backup, task.host)
def convertoyaml(file):
    converted_f = yaml.dump(file)
    return converted_f
def deploy_directory():
    directory_lst = [dir_fact, dir_config, dir_backup, dir_template, extra_vars]
    for directory in directory_lst:
        if not os.path.exists(directory):
            print(f'create directory {directory}')
            os.makedirs(directory)
        else:
            print(f'{directory} already exist!!!')
def savetodir(file_name, dir_name, hostname):
    os.chdir(dir_name)
    if dir_name == dir_fact:
        offset = '_fact.yml'
    if dir_name == dir_backup:
        offset = '_save.backup'
    if dir_name == dir_config:
        offset = '_new.cfg'
    if dir_name == extra_vars:
        offset = '.yaml'

    with open(f'{hostname}{offset}', 'w') as f:
        f.write(file_name)
    print(f'Have successfully save {file_name} to {dir_name}')
def push_templates(task):
    config = interface_templates(task)
    config += "\n\n"
    config += services_templates(task)
    config += "\n\n"
    config += routing_templates(task)
    config += "\n\n"
    config += bgp_templates(task)
    config += "\n\n"
    savetodir(config, dir_config, task.host)
def interface_templates(task):
    #Load FACT file into Host Attributes
    fact_file = task.run(
        task=load_yaml,
        file=f'{dir_fact}/{task.host}_fact.yml'
    )
    task.host['facts'] = fact_file.result
    #Load Trunk file into Host Attributes
    trunk_file = task.run(
        task=load_yaml,
        file=f'{dir_fact}/{task.host}_trunk.yml'
    )
    task.host['trunk'] = trunk_file.result

    #SETUP VLANS
    r = task.run(
        task=text.template_file,
        name="SETUP VLANS",
        template="vlans.j2",
        path="./templates/"
    )
    config = r.result
    config += "\n\n"

    # SETUP SPANNING TREE
    r = task.run(
        task=text.template_file,
        name="SETUP SPANNING TREE",
        template="stp.j2",
        path="./templates/"
    )
    config += r.result
    config += "\n\n"

    # SETUP INTERFACES
    r = task.run(
        task=text.template_file,
        name="IINTERFACE CONFIGURATION",
        template="base_intf.j2",
        path="./templates/"
    )
    config += r.result
    config += "\n\n"
    return config
def services_templates(task):
    #SETUP TIME & NTP
    r = task.run(
        task=text.template_file,
        name="SETUP TIME & NTP",
        template="ntp.j2",
        path="./templates/"
    )
    config = r.result
    config += "\n\n"

    #SETUP LOGGING & ARCHIVE
    r = task.run(
        task=text.template_file,
        name="SETUP LOGGIN & ARCHIVE",
        template="loggin.j2",
        path="./templates/"
    )
    config += r.result
    config += "\n\n"

    # SETUP AAA & TACACS
    r = task.run(
        task=text.template_file,
        name="SETUP AAA & TACACS",
        template="aaa.j2",
        path="./templates/"
    )
    config += r.result
    config += "\n\n"

    # SETUP KRONE JOB  & FTP
    r = task.run(
        task=text.template_file,
        name="SETUP KRON JOB & FTP SERVER",
        template="kron.j2",
        path="./templates/"
    )
    config += r.result
    config += "\n\n"

    return config
def get_bgp_peer():
    host_bgp_peer = []
    peer_bgp_list = []

    for host in nr.inventory.hosts.values():
        if host['asn'] != None and host['role'] != 'core-switch':
            host_bgp_peer.append(host)
    print(host_bgp_peer)
    for dev in host_bgp_peer:
        peer_bgp_dict = {}
        peer_bgp_dict['peer_name'] = dev.name
        peer_bgp_dict['peer_ip'] = dev.hostname
        peer_bgp_dict['peer_asn'] = dev['asn']
        peer_bgp_list.append(peer_bgp_dict)
    #print(bgp_neig)
    savetodir(convertoyaml(peer_bgp_list), extra_vars, 'bgp_peer')
def routing_templates(task):
    # SETUP OSPF
    r = task.run(
        task=text.template_file,
        name="SETUP OSPF",
        template="ospf.j2",
        path="./templates/"
    )
    config = r.result
    config += "\n\n"

    # SETUP MULTICAST
    r = task.run(
        task=text.template_file,
        name="SETUP MULTICAST",
        template="multicast.j2",
        path="./templates/"
    )
    config += r.result
    config += "\n\n"

    return config
def bgp_templates(task):
    # Load BGP file into Host Attributes
    bgp_file = task.run(
        task=load_yaml,
        file=f'{extra_vars}/bgp_peer.yaml'
    )
    task.host['bgp_peers'] = bgp_file.result

    r = task.run(
        task=text.template_file,
        name="SETUP BGP",
        template="bgp.j2",
        path="./templates/"
    )
    config = r.result
    config += "\n\n"

    return config

def main():
    print_title("Deploy INFRA DIRECTORY")
    deploy_directory()

    print_title("Get Host Fact Using NAPALM")
    result = nr.filter(site="CUCA", role="core-switch").run(task=get_host_fact)
    print_result(result)

    print_title("Perform a Backup before Changes")
    nr.filter(site="CUCA", role="core-switch").run(task=get_backup)

    print_title("Send Template to HOST")
    output = nr.filter(site="CUCA", role="core-switch").run(task=interface_templates)
    print_result(output)


if __name__ == '__main__':
    print_title("PUSH TEMPLATE to HOST")
    output = nr.filter(site="CUCA", role="core-switch").run(task=push_templates)
    #output = nr.filter(site="CUCA", role="core-switch").run(task=bgp_templates)
    print_result(output)
    #print(nr.inventory.hosts['CoreSPINEcuca01']['asn'])
    #print(nr.inventory.hosts['CoreSPINEcuca01']['vlans'])
    #print(get_bgp_peer())





