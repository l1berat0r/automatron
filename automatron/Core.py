from automatron.Devices import *
from automatron.Rules import *
from automatron.Utils import DebugPrint as _dp
import random
import time

class AutomatronCore(object):
	_devices = {}
	_state = {}
	_rules = []

	def __init__(self, config, **kwargs):
		pass

	def register_device(self, device):
		self._devices[device.name] = device

	def register_state(self, device):
		self._state[device] = {}

	def register_rule(self, device_name, rule_def):
		rule = Rule(self._devices[device_name], rule_def)
		self._rules.append(rule)
		rule.register(self)

	def send_command(self, device_name, msg):
		_dp("[Core] send_command: %s" % (device_name))
		self._devices[device_name].send_command(msg)
		

	def run(self):
		self.register_device(IRRemoteReceiver("phillips_remote", self))
		self.register_device(HUEControllReceiver("hue_state", self))
		self.register_device(IRRemoteTransmitter("hk3770", self))
		self.register_device(HUEControllTransmitter("hue_control", self))
		self.register_device(HUEStrobe("hue_strobe", self, hue_dev="hue_control"))

		self.register_state('hue')
		
		self.register_rule('phillips_remote', control_ir_remote) 
		self.register_rule('hue_state', hue_state_update)

		for d in self._devices.values():
			d.start()

		#while True:
		#	print("Checkout")
		#	time.sleep(10)
		#	print(self._devices[0].get_message())

		#	self._devices[1].send_command('KEY_VOLUMEDOWN')
				
		for d in self._devices.values():
			d.join()






