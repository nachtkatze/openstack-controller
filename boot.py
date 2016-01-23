import logging
import configparser
from novaclient import client as novaclient
from neutronclient.v2_0 import client as neutronclient

import utils

logging.basicConfig(level=logging.INFO)

class Booter():
    """
    Boots the corresponding topology.
    """
    def __init__(self, topo='fw_lb', *args, **kwargs):
        """
        Read from config.ini the configuration for the topologies.
        """
        self.topo = topo
        self.args = args
        self.kwargs = kwargs
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

    def up(self):
        """
        Call the booter to the corresponding topology class.
        """
        if self.topo == 'fw_lb':
            # config = self.parse_config(self.config['FwLbTopo'])
            config = utils.parse_config(self.config['FwLbTopo'])
            FwLbTopo(opts=config,
                session=self.kwargs['session'],
                token=self.kwargs['token'],
                neutron_endpoint=self.kwargs['neutron_endpoint']).up()

class FwLbTopo():
    """
    Implements the Firewall and LoadBalancer topology:
    - Two or three networks
    - FaaS and LbaaS
    - n instances as servers
    - m instances as storage nodes
    """

    def __init__(self,
        opts=None,
        net_names=['net0','net1'],
        net_prefixes=['10.0.0.0/24','10.0.1.0/24'],
        subnet_names=['subnet0','subnet1'],
        dns_nameservers=['8.8.8.8'],
        router_name='r',
        router_ports=['port0','port1'],
        flavors=['tiny_personalizada','tiny_personalizada'],
        images=['trusty-server-cloudimg-amd64-cnvr','trusty-server-cloudimg-amd64-cnvr'],
        secgroups=['default','default'],
        key_names=['my_key','my_key'],
        instances=[3,3],
        userdata=['userdata/balancer-ud.txt',
                  'userdata/server-ud.txt',
                  'userdata/storage-ud.txt'],
        session=None,
        token=None,
        neutron_endpoint=None,
        *args, **kwargs):
        """
        Initialize the topology. Authorization with nova and neutron using
        a session from keystone for nova and a token for neutron.
        """

        self.net_names = opts.get('net_names', net_names)
        self.net_prefixes = opts.get('net_prefixes', net_prefixes)
        self.subnet_names = opts.get('subnet_names', subnet_names)
        self.dns_nameservers = opts.get('dns_nameservers', dns_nameservers)
        self.router_name = opts.get('router_name', router_name)
        self.router_ports = opts.get('router_ports', router_ports)
        self.flavors = opts.get('flavors', flavors)
        self.images = opts.get('images', images)
        self.secgroups = opts.get('secgroups', secgroups)
        self.key_names = opts.get('key_names', key_names)
        self.instances = opts.get('instances', instances)
        self.userdata = opts.get('userdata', userdata)
        if session is None:
            raise ValueError('No session provided')
        if token is None:
            raise ValueError('No token provided')
        if neutron_endpoint is None:
            raise ValueError('No neutron_endpoint provided')
        self.session = session
        self.token = token
        self.neutron_endpoint = neutron_endpoint
        self.nets = []
        self.subnets = []
        self.servers = []

    def _create_net(self,neutron=None, net_name=None):
        """
        Create the network using the neutronclient. 
        """
        net_body = {'network':{
                'name': net_name,
                'admin_state_up': True
            }
        }
        net = neutron.create_network(body=net_body)
        return net['network']

    def _create_subnet(self, neutron=None, subnet_name=None, 
        subnet_prefix=None, net_id=None):
        """
        Create the subnet attached to a network using the
        neutronclient.
        """
        subnet_body = {'subnets':[{
                'cidr': subnet_prefix,
                'ip_version': 4,
                'network_id': net_id, 
                'name': subnet_name
            }
        ]}
        subnet = neutron.create_subnet(body=subnet_body)

        body = {'subnet':{
            'dns_nameservers': self.dns_nameservers 
        }}
        neutron.update_subnet(subnet['subnets'][0]['id'],
            body)

        return subnet['subnets'][0]

    def _create_router(self, neutron=None, nova=None, net_name=None,
        router_name=None, port_names=None):
        """
        Create router and add a port to the subnet in the net
        specified by the name
        """
        if isinstance(router_name, list):
            router_name = router_name[0]

        net_ids = list()
        if isinstance(net_name, list):
            for net in net_name:
                net = nova.networks.find(label=net)
                net_id = net.id
                net_ids.append(net_id)
        else:
            net = nova.networks.find(label=net_name)
            net_id = net.id
            net_ids.append(net_id)

        ext_net = nova.networks.find(label='ExtNet')
        ext_net_id = ext_net.id
        # net_ids = [net_id, ext_net_id]

        request = {'router': {'name': router_name,
                    'admin_state_up': True}}

        
        router = neutron.create_router(request)
        router_id = router['router']['id']

        neutron.add_gateway_router(router_id, {'network_id': ext_net_id})

        for net_id in net_ids:
            subnet_id = None
            for subnet in neutron.list_subnets()['subnets']:
                if subnet['network_id'] == net_id:
                    subnet_id = subnet['id']
                    neutron.add_interface_router(router_id,
                                             {'subnet_id': subnet_id})

    def _boot_instance(self, nova=None, image=None, flavor=None, nets=None,
        key_name=None, secgroups=None, name=None, userdata=None, count=1):
        """
        Boot the instace/s using the novaclient.
        """ 
        image = nova.images.find(name=image)
        flavor = nova.flavors.find(name=flavor)
        secgroups = [secgroups]
        nics = []
        if not isinstance(nets,list):
            nets = [nets]
        for net in nets:
            net = nova.networks.find(label=net)
            nics.append({'net-id':net.id})

        if userdata is None:
            f_userdata = None
        else:
            f_userdata = open(userdata,'r')

        instance = nova.servers.create(name=name, image=image, flavor=flavor,
            key_name=key_name, nics=nics, max_count=count, 
            min_count=count, security_groups=secgroups,
            userdata=f_userdata)    
 
    def up(self):
        """
        Set up the topology.
        """
        nova = novaclient.Client('2', session=self.session)
        neutron = neutronclient.Client(endpoint_url=self.neutron_endpoint,
            token=self.token)

        # Create nets
        logging.info('Creating networks...')
        try:
            for i in range(len(self.instances)):
                self.nets.append(self._create_net(neutron=neutron, 
                    net_name=self.net_names[i]))
        except Exception as e:
            logging.error('ERROR at creating networks:')
            logging.error(e)
        else:
            logging.info('Success!')

        # Create subnets into the created nets
        logging.info('Creating subnetworks...')
        try:
            for i in range(len(self.instances)):
                self.subnets.append(self._create_subnet(neutron=neutron,
                    subnet_name=self.subnet_names[i], 
                    subnet_prefix=self.net_prefixes[i],
                    net_id=self.nets[i]['id']))
        except Exception as e:
            logging.error('ERROR at creating subnetworks')
            logging.error(e)
        else:
            logging.info('Success!')

        # Create router and connect to net
        logging.info('Creating router...')
        try:
            self._create_router(neutron=neutron, nova=nova,
                net_name=self.net_names[0],
                router_name=self.router_name[0],
                port_names=self.router_ports)

            self._create_router(neutron=neutron, nova=nova,
                               net_name=self.net_names[1:],
                               router_name=self.router_name[1])
        except Exception as e:
            logging.error('ERROR at creating router')
            logging.error(e)
        else:
            logging.info('Success!')

        # Boot the load balancer instance
        logging.info('Booting load balancer instance')
        self._boot_instance(nova=nova, image=self.images[0],
                           flavor=self.flavors[0], nets=self.net_names[:2],
                           key_name=self.key_names[0],
                           secgroups=self.secgroups[0],
                           name='loadbalancer', userdata=self.userdata[0],
                           count=self.instances[0])
        logging.info('Success!')

        # Boot the server instances
        logging.info("Booting server instances")
        try:
            self._boot_instance(nova=nova, image=self.images[1], 
                flavor=self.flavors[1], nets=self.net_names[1:],
                key_name=self.key_names[1], 
                secgroups=self.secgroups[1],
                name='server', userdata=self.userdata[1],
                count=self.instances[1] )
        except Exception as e:
            logging.error('ERROR when creating servers')
            logging.error(e)
        else:
            logging.info('Success!')
    
        # Boot the storage instances
        logging.info('Booting storage instances')   
        try:
            self._boot_instance(nova=nova, image=self.images[2],
                flavor=self.flavors[2], nets=self.net_names[2],
                key_name=self.key_names[2],
                secgroups=self.secgroups[2],
                name='persist', count=self.instances[2] )
        except Exception as es:
            logging.error('ERROR when creating storage instances')
            logging.error(e)
        else:
            logging.info('Success!')
