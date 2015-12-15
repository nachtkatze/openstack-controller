import logging
import configparser
from novaclient import client as novaclient
from neutronclient.v2_0 import client as neutronclient

logging.basicConfig(level=logging.INFO)

class Dropper():
	"""
	Drops the corresponding topology.
	"""
	pass
