#!/usr/bin/env python

from config import bash

"""
notes
	need to check if docker is running
	start with "sudo service docker start" -- but this might be different on different systems

pseudocode
	do something and notice docker is requested
	get the current docker progress from the config.py file
"""

class Pier:

	"""
	Do things inside a docker.
	"""

	meta = {}

	def __init__(self,):
		"""
		Create a factory environment from instructions in the config, and setup or refresh if necessary.
		"""
		#---always check that docker is running
		#---! can we also get some useful information from this check?
		bash('docker ps')

	def run():
		"""
		Receive SOMETHING and do it inside the docker.
		! Needs mount and path information
		"""
		print(1231231)
