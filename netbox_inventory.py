#!/usr/bin/env python
from __future__ import print_function, unicode_literals
import requests
import json
import yaml
from pprint import pprint
import argparse
import sys
import netaddr

NETBOX_URL = 'http://10.30.10.243/api'
NETBOX_RESSOURCES = {
    'devices': '/dcim/devices/',
    'sites': '/dcim/sites/',
    'ip_addresses': '/ipam/ip-addresses/',
    'interfaces': '/dcim/interfaces/'
}
TOKEN = "4b26fc29a6bc33ba20acfcb77799419e4b9cd511"
HEADERS = {
    'Authorization': 'Token {}'.format(TOKEN),
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

def netbox_query(resources, query_params=None):
    '''
    
    :param resources: Devices, Sites, ip_address, Interfaces Consult API for Paramter Ressource
    :param query_params: If exist , filter by query_params eg ID, or Device Name
    :return:  API Result Using Ressource Query
    '''
    #print(f'query:\n{(NETBOX_URL + NETBOX_RESSOURCES[resources])}')
    return requests.get(NETBOX_URL + NETBOX_RESSOURCES[resources], params=query_params, headers=HEADERS)

nbx_devices = netbox_query('devices')  #get Netbox Device list and Device attribute via API

class Nbx_dev(object):
    username = 'admin'
    password = 'admin2019'
    def __init__(self, id, name, model, manufacturer, platform, device_role, ip, site):
        self.id = id
        self.name = name
        self.model = model
        self.manufacturer = manufacturer
        self.platform = platform
        self.device_role = device_role
        self.ip = ip
        self.site = site
        self.data = {}
        self.group = []
        self.asn = None

    @property
    def getos(self):
        if 'ios' in self.platform:
            self.os = 'ios'
        else:
            self.os = self.platform
        return 'ios'
    
    @property
    def getip(self):
        ipv4 = self.ip.split('/')
        return ipv4[0]

    def _getinf_id(self):
        intf_lst_id = []
        for intf in raw_interfaces_id():
            if intf['device']['name'] == self.name:
                intf_lst_id.append(intf['id'])
        return intf_lst_id

    def _getinf(self):
        intf_lst = []
        for id in self._getinf_id():
            id_str = str(id)
            intf_lst.append((raw_interfaces(id_str)))
        return intf_lst

    def _getipid(self):
        ip_lst_id = []
        for ip in raw_ip_id():
            if ip['interface']['device']['name'] == self.name:
                ip_lst_id.append(ip['id'])

        return ip_lst_id

    def _getipv4(self):
        ipv4_lst = []
        for id in self._getipid():
            id_str = str(id)
            ipv4_lst.append((raw_ipv4(id_str)))
        return ipv4_lst

    def get_data(self):
        return self.data

    def set_data(self, value):
        self.data.update(value)

    def setgroup(self, group_name):
        self.group.append(str(group_name))

    def getgroups(self):
        return self.group

    def get_parsed_intf(self):
        dev_intf_lst = [parsed_intf(intf) for intf in self._getinf()]
        return dev_intf_lst

    def get_parsed_ipv4(self):
        dev_ip_lst = [parsed_ipv4(ip) for ip in self._getipv4()]
        return dev_ip_lst

def raw_devices_lst():
    '''
    :return: list of Netbox Device and Return a raw list
    '''
    query_devices = nbx_devices.json()
    devices = [device for device in query_devices['results']]
    return devices
def raw_ip_id():
    '''
    
    :return:  Using API to query List of IP address, and return a raw list
    '''
    nbx_ip = netbox_query('ip_addresses')
    nbx_lst_result = (nbx_ip.json())['results']
    return nbx_lst_result
def raw_ipv4(ip_id):
    '''
      :param intf_id => interface id
      :return: Return a dictionnary using the ID Interface
      '''
    # print(NETBOX_URL + NETBOX_RESSOURCES['interfaces'] + f'{intf_id}/')
    query_ip = requests.get(NETBOX_URL + NETBOX_RESSOURCES['ip_addresses'] + f'{ip_id}/')
    return query_ip.json()
def raw_interfaces_id():
    '''
     coresw: [4,5,6]
    :return: Using API for get list of id interfaces and return a device dict with those id
    '''
    query_intf = netbox_query('interfaces')
    query_intf_js = query_intf.json()
    return query_intf_js['results']
def raw_interfaces(intf_id):
    '''
    :param intf_id => interface id
    :return: Return a dictionnary using the ID Interface
    '''
    #print(NETBOX_URL + NETBOX_RESSOURCES['interfaces'] + f'{intf_id}/')
    query_intf = requests.get(NETBOX_URL + NETBOX_RESSOURCES['interfaces'] + f'{intf_id}/')
    return query_intf.json()
def parsed_intf(intf_info):
    '''
    :param intf_info: get the raw interface Data
    :return: Return a Comprehensible dictionnary by filtering the interfaces key data
    '''
    intf = {}

    intf['name'] = intf_info['name']
    #if intf_info['form_factor']['label'] == 'Virtual':
    #    intf['type'] = 'Vlan'
    intf['description'] = intf_info['description']

    if intf_info["connected_endpoint"] and intf_info["connected_endpoint"] != 'null':
        #print(intf_info["connected_endpoint"].items())
        endpoint = {}
        endpoint['peer'] = intf_info['connected_endpoint']['device']['name']
        endpoint['peer_intf'] = intf_info['connected_endpoint']['name']
        #print(endpoint)
        intf['peer_connected'] = endpoint
        #print(intf['peer_connected'])

    #Check if Interface are tagged , it yes grab the vlan id
    if intf_info["tagged_vlans"] != 'null':
         for vlan in intf_info['tagged_vlans']:
             intf['tag'] = f'{vlan["vid"]}'

    if intf_info['connection_status'] and intf_info['connection_status'] != 'null':
            intf['status'] = intf_info['connection_status']['label']

    intf['mgt_only'] = intf_info['mgmt_only']
    return intf
def parsed_ipv4(ip):
    '''

    :param ip_lst: Get the Ip raw List
    :return: return List of IP with a comprehensible format
    '''
    nbx_ip_data = {}
    ipv4 = netaddr.IPNetwork(ip['address'])
    nbx_ip_data['ip'] = f"{ipv4.ip}"
    nbx_ip_data['subnet'] = f"{ipv4.netmask}"
    nbx_ip_data['rev_subnet'] = f"{ipv4.hostmask}"
    nbx_ip_data['name'] = ip['interface']['name']
    return nbx_ip_data
def mix_intftoip(dev):
    #Get list of interface
    complete_interfaces_lst = []
    for interface in dev.get_parsed_intf():
        copy_interface = dict(interface)
        for ip in dev.get_parsed_ipv4():
            if interface['name'] == ip['name']:
                copy_interface.update(ip)
                complete_interfaces_lst.append(copy_interface)
    return complete_interfaces_lst
def update_data_device(device):
    '''
    :param device_lst: Get the Device Object List
    :param Get and Copy the Original IPlist  
    :return: Match the IP to the Device, and if match, Update the Device Object with the IP address
    '''
    intf_data_lst = mix_intftoip(device)
    intf_data = {'intf': intf_data_lst}
    device.set_data(intf_data)
def netboxtodevlist():
    '''
    
    :return: Get the List of Netbox and Create Object Class Device
    '''
    nbx_obj_lst = []
    for device in raw_devices_lst():
        nbx_obj = Nbx_dev(
            device['id'],
            device['name'],
            device['device_type']['model'],
            device['device_type']['manufacturer']['name'],
            device['platform']['slug'],
            device['device_role']['slug'],
            device['primary_ip4']['address'],
            device['site']['name'],
        )
        nbx_obj.asn = device['custom_fields']['device_asn']
        nbx_obj.setgroup(device['device_role']['slug'])
        nbx_obj.setgroup('global')
        nbx_obj_lst.append(nbx_obj)
    return nbx_obj_lst
def export_to(device_lst):
    '''
    
    :param device_lst: Get the List of Device Object
    :return: Inventory format as python Dictionnary
    '''
    inventory = {}
    for dev in device_lst:
        host_data = {}
        host_data['username'] = dev.username
        host_data['password'] = dev.password
        host_data['hostname'] = dev.getip
        host_data['platform'] = dev.getos
        host_data['groups'] = dev.getgroups()
        host_data['data'] = {}
        host_data['data']['site'] = dev.site
        host_data['data']['device_name'] = dev.name
        host_data['data']['role'] = dev.device_role
        host_data['data']['model'] = dev.model
        host_data['data']['asn'] = dev.asn
        host_data['data']['interfaces'] = dev.data['intf']
        inventory[host_data['data']['device_name']] = host_data
    return inventory
def displayHost(device_name, device_lst=netboxtodevlist()):
        for dev in device_lst:
            if device_name == dev.name:
                #return dev.__dict__
                return dev
def trash():
    # Get List of Formated Devices:

    dicttest = {
        'asn': 6500
    }
    #update_data_vars(netbox_device_lst, dicttest)

    # print(raw_ip_id()[0].items())
    # print(parsed_ip(raw_ip_id()))
    # print(netbox_device_lst[0].data)
    # obj1= netbox_device_lst[0].__dict__
    # print(yaml.dump(obj1))
    # print(export_to(netbox_device_lst))
    #pprint(yaml.dump(export_to(netbox_device_lst)))
    with open('asn_test', 'r') as f:
        for obj in f.readlines():
            print(yaml.load(obj))
    if args.device_name:
        print(displayHost(args.device_name))
    if args.device_name and args.file_name:
        update_device[args.device_name] = args.file_name
        # print(f'{args.device_name, args.file_name}')

        # update_data_netip(netbox_device_lst, parsed_ip(raw_ip_id()))
    update_device = {}
    if update_device:
        update_data_vars(**update_device)

    def update_data_vars(device_name, vars_file, device_lst=netboxtodevlist()):
        device_namelist = [dev.name for dev in device_lst]
        if device_name in device_namelist:
            idx = device_namelist.index(device_name)
            print(device_lst[idx].data)
            with open(vars_file, 'r') as f:
                for line in f.readlines():
                    print(type(yaml.load(line)))
                    device_lst[idx].data.update(yaml.load(line))
            print(f'{device_lst[idx].name} -> update :\n{device_lst[idx].data}')
            print(device_lst[idx].data)
        else:
            return f"This Device {device_name} do not exist !!!"
def main():

    if len(sys.argv) <= 1:
        print("Use {} -h or --help to get script help menu".format(sys.argv[0]))

    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('-e', '--export', help="export [filename.yml] [destination]")
        parser.add_argument('-d', '--device', action='store', dest='device_name', help="device [device name]")
        parser.add_argument('-u', '--update', action='store', dest='file_name', help="update [file variable]")
        args = parser.parse_args()

        #GET NETBOX DEVICE LIST
        netbox_device_lst = netboxtodevlist()
        #UPDATE DATA VARS TO EACH DEVICE
        for device in netbox_device_lst:
            update_data_device(device)

        if args.export:
            inventory_name = sys.argv[2]
            with open(inventory_name, 'w') as f:
                f.write(f'---\n{yaml.dump(export_to(netbox_device_lst))}\n...') #Convert the Py Dict to Yaml Format

if __name__ == '__main__':
    #for device in netboxtodevlist():
    #    if device.name == "dcgca.esg.border":
    #        print(device.asn)
            #print(device.get_parsed_intf())
            #print(device.get_parsed_ipv4())
     #       update_data_device(device)
     #       print(device.data)
    main()












