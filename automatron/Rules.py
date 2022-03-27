from automatron.Utils import DebugPrint as _dp
import json
import datetime
import sys

class Rule(object):
	def __init__(self, src, rule_def):
		_dp("Rule for %s initialized" % src.name)

		self._src = src
		self._def = rule_def
		self._src.register_rule(self)

	def register(self, core):
		self._core = core

	def evaluate(self, message):
		self._def(self, self._src, message)

def hue_state_update(rule, dev, msg):
	_dp("-hue_state_update %s" %  datetime.datetime.now().isoformat())
	sys.stdout.flush()
	rule._core._state['hue'] = msg.message


def control_ir_remote(rule, dev, msg):
	_dp("-control_hk3770_ir_remote: %s" % msg)

	cmd_raw = msg.message
	cmd_list = cmd_raw.strip().split(b' ')

	remote = cmd_list[3].decode()
	cmd_num = int(cmd_list[1], 16)
	cmd = cmd_list[2].decode()
	
	_dp("--command parsed: %s, %s, %s" % (cmd, cmd_num, remote))

	cmd_map = {
		'philips': {
			'KEY_POWER': {'key': 'KEY_POWER', 'once': True, 'dev': 'hk3770'},
			'KEY_VOLUMEUP': {'key': 'KEY_VOLUMEUP', 'once': False, 'dev': 'hk3770'},
			'KEY_VOLUMEDOWN': {'key': 'KEY_VOLUMEDOWN', 'once': False, 'dev': 'hk3770'},
			'KEY_BLUE': {'key': ('ROOM_ON', 'LIVING_ROOM', 'LIGHTS'), 'once': False, 'dev': 'hue_control'},
			'KEY_YELLOW': {'key': ('ROOM_OFF', 'LIVING_ROOM', 'LIGHTS'), 'once': False, 'dev': 'hue_control'}
		},
		'rgb': {
			'KEY_POWER': {'key': ('ROOM_ON', 'LIVING_ROOM', 'LIGHTS'), 'once': False, 'dev': 'hue_control'},
			'KEY_POWER2': {'key': ('ROOM_OFF', 'LIVING_ROOM', 'LIGHTS'), 'once': False, 'dev': 'hue_control'},
			'KEY_UP': {'key': ('CHG_BRI', 'LIVING_ROOM', 'LIGHTS', 25), 'once': False, 'dev': 'hue_control'},
			'KEY_DOWN': {'key': ('CHG_BRI', 'LIVING_ROOM', 'LIGHTS', -25), 'once': False, 'dev': 'hue_control'},
			'KEY_F1': {'key': ('TGL_STATE', 'LIVING_ROOM', 'SENSORS', ['config', 'on']), 'once': False, 'dev': 'hue_control'},
			'KEY_F2': {'key': ('TGL_STROBE', 'LIVING_ROOM', 'LIGHTS'), 'once': False, 'dev': 'hue_strobe'},
			'KEY_F3': {'key': ('TGL_FADE', 'LIVING_ROOM', 'LIGHTS'), 'once': False, 'dev': 'hue_strobe'},
			'KEY_F4': {'key': ('TGL_SMOOTH', 'LIVING_ROOM', 'LIGHTS'), 'once': False, 'dev': 'hue_strobe'},
			'KEY_RED': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 64603, 'sat': 254}), 'once': False, 'dev': 'hue_control'},
			'KEY_GREEN': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 24432, 'sat': 254}), 'once': False, 'dev': 'hue_control'},
			'KEY_BLUE': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 46014, 'sat': 254}), 'once': False, 'dev': 'hue_control'},
			'KEY_W': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 8597, 'sat': 140}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F1': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 1321, 'sat': 254}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F2': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 41039, 'sat': 192}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F3': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 45061, 'sat': 254}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F4': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 5926, 'sat': 214}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F5': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 41040, 'sat': 225}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F6': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 46008, 'sat': 254}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F7': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 25140, 'sat': 55}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F8': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 34516, 'sat': 234}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F9': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 47492, 'sat': 215}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F10': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 10643, 'sat': 237}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F11': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 44720, 'sat': 254}), 'once': False, 'dev': 'hue_control'},
			'KEY_FN_F12': {'key': ('CHG_STATE', 'LIVING_ROOM', 'LIGHTS', {'hue': 55751, 'sat': 214}), 'once': False, 'dev': 'hue_control'}
		}
	}

	if remote in cmd_map and cmd in cmd_map[remote]:
		cmd_map[remote][cmd]['state'] = rule._core._state
		rule._core.send_command(cmd_map[remote][cmd]['dev'], {'cmd': cmd_map[remote][cmd], 'num': cmd_num})


