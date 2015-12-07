import argparse
import os

parser = argparse.ArgumentParser(description='''
   	Control some operations on the OpenStack module
	-----------------------------------------------
	- Creation of net topologies
	- Management of these topologies
	''')

parser.add_argument('opt', metavar='operation', type=str, choices=['boot','shutdown'],
	help='operation to perform: boot or shutdown')
parser.add_argument('--topo', default='fw_lb', 
	help='name of the topology to create, default is fw_lb')
parser.add_argument('--net-name', default='net0', dest='net_name',
	help='net name, default is net0')
parser.add_argument('--net-prefix', default='10.0.0.0/24', dest='net_prefix',
	help='net prefix for the net, default is 10.0.0.0/24')
parser.add_argument('--subnet-name', default='subnet0', dest='subnet_name',
	help='subnet name, default is subnet0')
parser.add_argument('--flavor', default='tiny_personalizada',
	help='flavor of the new instances, default is tiny_personalizada')
parser.add_argument('--image', default='trusty-server-cloudimg-amd64-cnvr',
	help='image from which to create the instances, default is trusty-server-cloudimg-amd64-cnvr')
parser.add_argument('--secgroup', default='default',
	help='security group in which to add the instances, default is default')
parser.add_argument('--key-name', default='my_key', dest='key_name',
	help='security key to be used')
parser.add_argument('-i','--instances', metavar='n', type=int, default=3,
	help='n instances of the image, default is 3')
parser.add_argument('--shut-all', action='store_true', dest='shut_all',
	help='shut all: instances and nets')

args = parser.parse_args()

def nova_connect():
	from os import environ as env
	from keystoneclient.auth.identity import v3
	from keystoneclient import session

	auth = v3.Password(auth_url=env['OS_AUTH_URL'],
		username=env['OS_USERNAME'],
		password=env['OS_PASSWORD'],
		project_name=env['OS_TENANT_NAME'],
		user_domain_name=env['OS_USER_DOMAIN_ID'],
		project_domain_name=env['OS_PROJECT_DOMAIN_ID'])

	sess = session.Session(auth=auth)
	return sess

def neutron_connect():
	from os import environ as env
	import keystoneclient.v3.client as ksclient
	from neutronclient.v2_0 import client as neutronclient
	keystone = ksclient.Client(auth_url=env['OS_AUTH_URL'],
                           username=env['OS_USERNAME'],
                           password=env['OS_PASSWORD'],
                           tenant_name=env['OS_TENANT_NAME'],
                           region_name=env['OS_REGION_NAME'])
	endpoint_url = keystone.service_catalog.url_for(service_type='network')
	token = keystone.auth_token
	neutron_endpoint = keystone.service_catalog.url_for(service_type='network') 
	return token, neutron_endpoint

if __name__ == '__main__':
	import logging
	logging.basicConfig(level=logging.INFO)
	session = nova_connect()
	token, neutron_endpoint = neutron_connect()
	args = vars(args)
	args['session'] = session
	args['token'] = token
	args['neutron_endpoint'] = neutron_endpoint


	if args['opt'] == 'boot':
		import boot
		logging.debug('Starting booting process...')	
		boot.Booter(**args).up()

	elif args['opt'] == 'shutdown':
		import delete
		logging.debug('Starting shutdown process...')
		delete.shutdown(**vars(args))
