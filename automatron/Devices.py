from automatron.Rules import *
from automatron.Utils import DebugPrint as _dp
import threading
import time
import socket
import uuid
import requests
import random


class AutomatronDevice(threading.Thread):
	FailThreshold = 10	

	def __init__(self, name, core, **kwargs):
		threading.Thread.__init__(self)
		self.fail_count = 0
		self.rules = []

		if name is None:
			name = uuid.uuid4()

		self._name = name
		self._core = core
		self._kwargs = kwargs

		_dp("Device %s initialized" % name)		

	def _init_device(self):
		pass

	def _update_state(self):
		pass

	def register_rule(self, rule):
		self.rules.append(rule)


class ReceiverDevice(AutomatronDevice):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.messages = []
		self.fail_count = 0
		self._sleep = None
		self._init_device()

	def run(self):
		_dp("Device %s running" % self._name)		
		while self.fail_count < 10:
			try:
				message = self.listen()
				if message.emmit:
					#self.messages.append(message)
					
					for r in self.rules:
						r.evaluate(message)

			except DeviceError as e:
				if not e.reinit:
					raise e
				else:
					self._init_device()
					self.fail_count += 1

			if self._sleep is not None:
				time.sleep(self._sleep)

	def get_message(self):
		if len(self.messages):
			return self.messages.pop(0)
		else:
			return None

		

class TransmitterDevice(AutomatronDevice):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.commands = []
		self.fail_count = 0
		self._mutex = threading.Lock()
		self.command_waiting = threading.Condition(self._mutex)
		self._init_device()


	def run(self):
		_dp("Device %s running" % self._name)		
		while True:
			self.command_waiting.acquire()
			self.command_waiting.wait(0.01)
	
			while len(self.commands):
				c = self.commands.pop(0)
				try:
					self._process_command(c)
				except DeviceError as e:
					self._init_device(True)
					self.commands.insert(0, c)

			self._update_state()

			self.command_waiting.release()

	def send_command(self, cmd):
		#_dp("[%s] - send_command: %s" % (self.name, cmd))
		self.command_waiting.acquire()
		self.commands.append(cmd)
		self.command_waiting.notify()
		self.command_waiting.release()

class HUEControllReceiver(ReceiverDevice):
	def _init_device(self, reinit=False):
		self._url = "url"
		self._username = "username"
		self._sleep = 1

	def listen(self):
		try:
			lights_state_r = requests.get("%s/api/%s/lights" % (self._url, self._username))
			sensors_state_r = requests.get("%s/api/%s/sensors" % (self._url, self._username))
		except Exception as e:
			return DeviceMessage({'LIGHTS': '', 'SENSORS': ''})

		return DeviceMessage({'LIGHTS': lights_state_r.json(), 'SENSORS': sensors_state_r.json()})

class HUEControllTransmitter(TransmitterDevice):
	devices_location = {
		'LIGHTS': {
			'LIVING_ROOM': ['1','2','4']
		},
		'SENSORS': {
			'LIVING_ROOM': ['3']
		}	
	}
	params = {
		'LIGHTS': {'state': ['on', 'bri', 'hue', 'sat'], 'config': []},
		'SENSORS': {'state': [], 'config': ['on']}
	}


	def _init_device(self, reinit=False):
		self._url = "http://192.168.0.150"
		self._username = "FLPYo-2Oe1NZEM47h5KW86K1QfLeSOh2CPFTSYIs"

	def _set_device(self, device, nr, option, state):
		#_dp("[%s] - _set_device: %s - %s" % (self.name, nr, state))
		r = requests.put("%s/api/%s/%s/%d/%s" % (self._url, self._username, device.lower(), int(nr), option), data=json.dumps(state))

	def _process_command(self, cmd):
		_dp("[%s] - _process_command" % (self.name))

		args  = cmd['cmd']['key']
		once = cmd['cmd']['once']
		num = cmd['num']
		state = cmd['cmd']['state']['hue']

		action = args[0]
		room = args[1]
		device = args[2]

		if len(args) > 3:
			params = args[3]

		devices = HUEControllTransmitter.devices_location[device][room]

		device_state = dict(map(lambda dd: (dd[0], {k: dd[1]['state'][k] for k in HUEControllTransmitter.params[device]['state'] if k in dd[1]['state']}), 
				       filter(lambda d: d[0] in devices, state[device].items())))

		device_config = dict(map(lambda dd: (dd[0], {k: dd[1]['config'][k] for k in HUEControllTransmitter.params[device]['config'] if k in dd[1]['config']}), 
				       filter(lambda d: d[0] in devices, state[device].items())))

		update_state = False
		update_config = False
		#_dp("[%s] -- orig_state %s" % (self.name, state))
		#_dp("[%s] -- device_state %s" % (self.name, device_state))

		if action == 'ROOM_ON':
			update_state = True
			for d, s in device_state.items():
				s['on'] = True

		if action == 'ROOM_OFF':
			update_state = True
			for d, s in device_state.items():
				s['on'] = False
		
		if action == 'ROOM_TGL':
			update_state = True
			for d, s in device_state.items():
				s['on'] = not s['on']

		if action == 'CHG_BRI':
			update_state = True
			for d, s in device_state.items():
				s['bri'] += params
				if s['bri'] < 10:
					s['bri'] = 10
				if s['bri'] > 255:
					s['bri'] = 255

		if action == 'CHG_STATE':
			update_state = True
			for d, s in device_state.items():
				s.update(params)

		if action == 'TGL_STATE':
			update_config = True
			for d, c in device_config.items():
				c[params[1]] = not c[params[1]]

		if update_state:
			for d, s in device_state.items():
				self._set_device(device, d, 'state', s)
				state[device][d]['state'] = s

		if update_config:
			for d, c in device_config.items():
				self._set_device(device, d, 'config', c)
				state[device][d]['config'] = c
	

class HUEStrobe(TransmitterDevice):
	strobe_period = 1.0
	smooth_period = 1.0
	fade_period = 2.0

	def _strobe(self):
		_dp("Strobe Flash")
		self._core.send_command(self._hue_dev, {'cmd': {'key': ('ROOM_TGL', self._room, self._device), 'once': False, 'dev': 'hue_control', 'state': self._core._state}, 'num': 1})
		if self._strobing:
			threading.Timer(self.strobe_period, HUEStrobe._strobe, (self,)).start()

	def _fade(self):
		_dp("Fade flash")
		hue = random.randint(0, 65534)
		sat = random.randint(0, 254)

		self._core.send_command(self._hue_dev, {'cmd': {'key': ('CHG_STATE', self._room, self._device, {'sat': sat, 'hue': hue}), 
						       'once': False, 'dev': 'hue_control', 'state': self._core._state}, 'num': 1})

		if self._fading:
			threading.Timer(self.fade_period, HUEStrobe._fade, (self,)).start()

	def _smooth(self):
		_dp("Smooth flash")
		hue = self._core._state['hue']['LIGHTS']['1']['state']['hue']
		sat = self._core._state['hue']['LIGHTS']['1']['state']['sat']
		hue += random.randint(0, 2000) - 1000
		sat += random.randint(0, 40) - 20

		if hue > 65534:
			hue = 65534

		if hue < 0:
			hue = 0

		if sat > 254:
			sat = 254

		if sat < 0:
			sat = 0

		self._core.send_command(self._hue_dev, {'cmd': {'key': ('CHG_STATE', self._room, self._device, {'sat': sat, 'hue': hue}), 
						       'once': False, 'dev': 'hue_control', 'state': self._core._state}, 'num': 1})

		if self._smoothing:
			threading.Timer(self.smooth_period, HUEStrobe._smooth, (self,)).start()

	def _init_device(self, reinit=False):
		self._strobing = False
		self._fading = False
		self._smoothing = False
		self._hue_dev = self._kwargs['hue_dev']

	def _process_command(self, cmd):
		_dp("[%s] - _process_command" % (self.name))

		args  = cmd['cmd']['key']
		once = cmd['cmd']['once']
		num = cmd['num']

		self._action = args[0]
		self._room = args[1]
		self._device = args[2]		

		if self._action == 'TGL_STROBE':
			self._strobing = not self._strobing

		if self._action == 'TGL_FADE':
			self._fading = not self._fading

		if self._action == 'TGL_SMOOTH':
			self._smoothing = not self._smoothing

		if self._strobing:
			_dp("Start Strobing")
			threading.Timer(self.strobe_period, HUEStrobe._strobe, (self,)).start()

		if self._fading:
			_dp("Start Fading")
			threading.Timer(self.fade_period, HUEStrobe._fade, (self,)).start()

		if self._smoothing:
			_dp("Start Smoothing")
			threading.Timer(self.smooth_period, HUEStrobe._smooth, (self,)).start()
				

class IRRemoteTransmitter(TransmitterDevice):
	def _init_device(self, reinit=False):
		self._socket = socket.socket(socket.AF_UNIX)
		self._socket.connect("/var/run/lirc/lircd")
		self._socket.setblocking(True)

		self.transmitting = False
		self.last_update = time.time()
		self.last_key = None

	def _process_command(self, cmd):
		_dp("[%s] - _process_command: %s" % (self.name, cmd))

		key = cmd['cmd']['key']
		once = cmd['cmd']['once']
		num = cmd['num']

		if self.transmitting and key != self.last_key:
			self._send_stop(self.last_key)
		
		if num > 1 and not self.transmitting:
			self._send_start(key)
		elif not self.transmitting:
			self._send_once(key)
		
		self.last_key = key
		self.last_update = time.time()

	def _send(self, how, cmd):
		_dp("[%s] - _send: %s, %s" % (self.name, how, cmd))
		try:
			self._socket.sendall(("%s hk %s\n" % (how, cmd)).encode())
		except Exception as e:
			raise DeviceError(str(e), True)

	def _send_once(self, cmd):
		self._send('SEND_ONCE', cmd)

	def _send_start(self, cmd):
		self._send('SEND_START', cmd)
		self.transmitting = True

	def _send_stop(self, cmd):
		self._send('SEND_STOP', cmd)
		self.transmitting = False
	
	def _update_state(self):
		#_dp("[%s] - _update_state" % self.name)

		if self.transmitting and time.time() - self.last_update > 0.25:
			self._send_stop(self.last_key)


class IRRemoteReceiver(ReceiverDevice):
	def _init_device(self):
		self._socket = socket.socket(socket.AF_UNIX)
		self._socket.connect("/var/run/lirc/lircrcv")
		

	def listen(self):
		msg = self._socket.recv(1024)
		return DeviceMessage(msg.strip())

class DeviceMessage(object):
	def __init__(self, message):
		self.message = message
		self.emmit = True
		self.timestamp = time.time()

	def __str__(self):
		return str(self.message)


class DeviceError(Exception):
	def __init__(self, message, reinit=False):
		super().__init__(message)
		self.reinit = reinit
