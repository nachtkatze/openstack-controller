import time
import logging
import configparser
from novaclient import client as novaclient
from neutronclient.v2_0 import client as neutronclient

import utils
from neutronapi import NeutronIF

logging.basicConfig(level=logging.INFO)

class Dropper():
    """
    Drops the corresponding topology.
    """
    def __init__(self, topo='fw_lb', *args, **kwargs):
        """
        Read from config file the configuration for the topologies.
        """
        self.topo = topo
        self.args = args
        self.kwargs = kwargs
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

    def drop(self):
        """
        Call the dropper to the corresponding topology class or
        if the shut is for all elements, drops everything.
        """
        if self.topo == 'all':
            AllTopo(opts=None,
                session=self.kwargs['session'],
                token=self.kwargs['token'],
                neutron_endpoint=self.kwargs['neutron_endpoint']).drop()

        if self.topo == 'fw_lb':
            config = utils.parseconfig(sekf.config['FwLbTopo'])


class AllTopo():
    """
    Represents the all-elements instance. Dropper calls it to drop
    all the elements in the tenant.
    """

    def __init__(self, opts=None, session=None,
        token=None, neutron_endpoint=None, *args, **kwargs):

        if session is None:
            raise ValueError('No session provided')
        if token is None:
            raise ValueError('No token provided')
        if neutron_endpoint is None:
            raise ValueError('No neutron_endpoint provided')
        self.session = session
        self.token = token
        self.neutron_endpoint = neutron_endpoint

    def drop(self):
        """
        Drops the All Topology, which is the topology of all the elements
        in the tenant,
        """
        nova = novaclient.Client('2', session=self.session)
        neutron = neutronclient.Client(endpoint_url=self.neutron_endpoint,
            token=self.token)
        neutron_if = NeutronIF()

        # Remove FWaaS
        logging.info('Removing FWaaS')
        try:
            for fw in neutron_if.firewall_list():
                neutron_if.firewall_delete(fw.get('id'))

            for policy in neutron_if.firewall_policy_list():
                neutron_if.firewall_policy_delete(policy.get('id'))

            for rule in neutron_if.firewall_rule_list():
                neutron_if.firewall_rule_delete(id_=rule.get('id'))
        except Exception as e:
            logging.error('ERROR at removing FWaaS')
            logging.error(e)
        else:
            logging.info('Success!')

        # Deallocate floating IPs
        logging.info('Deallocating floating IPs')
        try:
            floating_ips = nova.floating_ips.list()
            for f_ip in floating_ips:
                nova.servers.remove_floating_ip(server=f_ip.instance_id,
                                           address=f_ip.ip)
                nova.floating_ips.delete(f_ip.id)
        except Exception as e:
            logging.error('ERROR at deallocating floating IPs')
            logging.error(e)
        else:
            logging.info('Success!')

        # Delete routers
        logging.info('Deleting routers...')
        try:
            routers = neutron_if.router_list()
            for router in routers:
                id_ = router['id']
                # Delete gateway
                neutron_if.router_gateway_clear(router_id=id_)
                # Get router ports
                interfaces = neutron_if.router_port_list(router_id=id_)
                # Delete interfaces the router is connected to
                for interface in interfaces:
                    port_id = interface.get('id')
                    neutron_if.router_interface_delete(router_id=id_,
                                                       port_id=port_id)
                # Delete router
                neutron_if.router_delete(router_id=id_)
        except Exception as e:
            logging.error('Error at deleting routers')
            logging.error(e)
        else:
            logging.info('Success!')

        # Delete instances
        logging.info('Deleting instances...')
        try:
            servers = nova.servers.list()
            for server in servers:
                server.delete()
        except Exception as e:
            logging.error('Error at deleting the instances')
            logging.error(e)
        else:
            logging.info('Success!')

        time.sleep(5)

        # Delete networks
        logging.info('Deleting subnets and nets...')
        try:
            networks = neutron.list_networks()['networks']
            for network in networks:
                if network['name'] == 'ExtNet':
                    continue
                id_ = network['id']
                for subnet in network['subnets']:
                    neutron.delete_subnet(subnet)
                neutron.delete_network(id_)
        except Exception as e:
            logging.error('Error at deleting the subnets and nets')
            logging.error(e)
        else:
            logging.info('Success!')
