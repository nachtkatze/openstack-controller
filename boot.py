import logging
import configparser
from novaclient import client as novaclient
from neutronclient.v2_0 import client as neutronclient

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

	def parse_config(self, config):
		"""
		Parse the config from config.ini file. Parse to a list
		in case of comma-separated values.
		"""
		c = dict()
		for k,v in config.items():
			c[k] = v.split(',')	
		return c

	def up(self):
		"""
		Call the booter to the corresponding topology class.
		"""
		if self.topo == 'fw_lb':	
			config = self.parse_config(self.config['FwLbTopo'])
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
	- m instances as persistences nodes
	"""

	def __init__(self, 
		opts=None,
        net_names=['net0','net1'],
      	net_prefixes=['10.0.0.0/24','10.0.1.0/24'],
      	subnet_names=['subnet0','subnet1'],
      	flavors=['tiny_personalizada','tiny_personalizada'],
      	images=['trusty-server-cloudimg-amd64-cnvr','trusty-server-cloudimg-amd64-cnvr'],
      	secgroups=['default','default'],
      	key_names=['my_key','my_key'],
      	instances=[3,3],
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
		self.flavors = opts.get('flavors', flavors)
		self.images = opts.get('images', images)
		self.secgroups = opts.get('secgroups', secgroups)
		self.key_names = opts.get('key_names', key_names)
		self.instances = opts.get('instances', instances)
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
		return subnet['subnets'][0]

	def _boot_instance(self, nova=None, image=None, flavor=None, nets=None,
		key_name=None, secgroups=None, name=None, count=1):
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
		instance = nova.servers.create(name=name, image=image, flavor=flavor,
			key_name=key_name, nics=nics, max_count=count, 
			min_count=count, security_groups=secgroups)			
 
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
		except:
			logging.error('ERROR at creating networks')
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
		except:
			logging.error('ERROR at creating subnetworks')
		else:
			logging.info('Success!')

		# Boot the server instances
		logging.info("Booting server instances")
		try:
			self._boot_instance(nova=nova, image=self.images[0], 
				flavor=self.flavors[0], nets=self.net_names,
				key_name=self.key_names[0], 
				secgroups=self.secgroups[0],
				name='server', count=self.instances[0] )
		except:
			logging.error('ERROR when creating servers')
		else:
			logging.info('Success!')
	
		# Boot the persistence instances
		logging.info('Booting persistence instances')	
		try:
			self._boot_instance(nova=nova, image=self.images[1],
				flavor=self.flavors[1], nets=self.net_names[1],
				key_name=self.key_names[1],
				secgroups=self.secgroups[1],
				name='persist', count=self.instances[1] )
		except:
			logging.error('ERROR when creating persistence instances')
		else:
			logging.info('Success!')
