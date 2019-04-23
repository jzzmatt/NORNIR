#!/usr/bin/env python

from nornir import InitNornir
from nornir.plugins.functions.text import print_title, print_result
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

def get_host_fact(task):
    get_fact = task.run(task=networking.napalm_get, getters=['facts'])
    #task.host['facts'] = get_fact.result
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
    directory_lst = [dir_fact, dir_config, dir_backup, dir_template]
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

    with open(f'{hostname}{offset}', 'w') as f:
        f.write(file_name)
    print(f'Have successfully save {file_name} to {dir_name}')

def main():
    print_title("Deploy INFRA DIRECTORY")
    #Deploy INFRA DIRECTORY
    deploy_directory()
    #RUN DEVICE FACT
    #print_title("Get Host Fact Using NAPALM")
    #result = nr.filter(site="VICTORIA", role="test-device").run(task=get_host_fact)
    #print_result(result)

    #RUN A PRE BACKUP BEFORE CHANGES
    print_title("Perform a Backup before Changes")
    nr.filter(site="VICTORIA", role="test-device").run(task=get_backup)
    #print_result(result)
    #file = nr.inventory.hosts['CSR1000v-lab']['facts']

if __name__ == '__main__':
    main()


