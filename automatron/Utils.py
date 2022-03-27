DEBUG = False

class DebugPrint(object):
	_debug = DEBUG

	def __init__(self, msg):
		if self._debug:
			print(msg)

			f = open("/home/pi/workbench/ir_control/automatron.log", "a")
			f.write("%s\n" % msg)
			f.close()
