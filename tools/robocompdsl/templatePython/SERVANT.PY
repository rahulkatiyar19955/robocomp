[[[cog

import sys
sys.path.append('/opt/robocomp/python')

import cog
def A():
	cog.out('<@@<')
def Z():
	cog.out('>@@>')
def TAB():
	cog.out('<TABHERE>')

from dsl_parsers.dsl_factory import DSLFactory
from dsl_parsers.parsing_utils import IDSLPool
includeDirectories = theIDSLPaths.split('#')
component = DSLFactory().from_file(theCDSL, include_directories=includeDirectories)
if component == None:
	raise ValueError('SERVANT.PY: Can\'t locate %s' % theCDSLs)

modulePool = IDSLPool(theIDSLs, includeDirectories)
module = modulePool.moduleProviding(theInterface)
if module == None:
	raise ValueError('SERVANT.PY: Can\'t locate %s' % theIDSLs)


]]]
[[[end]]]
#
# Copyright (C)
[[[cog
A()
import datetime
cog.out(' '+str(datetime.date.today().year))
Z()
]]]
[[[end]]]
 by YOUR NAME HERE
#
#    This file is part of RoboComp
#
#    RoboComp is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RoboComp is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RoboComp.  If not, see <http://www.gnu.org/licenses/>.
#

import sys, os, Ice

ROBOCOMP = ''
try:
	ROBOCOMP = os.environ['ROBOCOMP']
except:
	print('$ROBOCOMP environment variable not set, using the default value /opt/robocomp')
	ROBOCOMP = '/opt/robocomp'
if len(ROBOCOMP)<1:
	raise RuntimeError('ROBOCOMP environment variable not set! Exiting.')


additionalPathStr = ''
icePaths = []
try:
	icePaths.append('/opt/robocomp/interfaces')
	SLICE_PATH = os.environ['SLICE_PATH'].split(':')
	for p in SLICE_PATH:
		icePaths.append(p)
		additionalPathStr += ' -I' + p + ' '
except:
	print('SLICE_PATH environment variable was not exported. Using only the default paths')
	pass

[[[cog
cog.outl('ice_'+theInterface+' = False')
cog.outl('for p in icePaths:')
cog.outl('<TABHERE>print(\'Trying\', p, \'to load ' + theInterface + '.ice\')')
cog.outl('<TABHERE>if os.path.isfile(p+\'/'+theInterface+'.ice\'):')
cog.outl('<TABHERE><TABHERE>print(\'Using\', p, \'to load '+theInterface+'.ice\')')
cog.outl('<TABHERE><TABHERE>preStr = "-I/opt/robocomp/interfaces/ -I"+ROBOCOMP+"/interfaces/ " + additionalPathStr + " --all "+p+\'/\'')
cog.outl('<TABHERE><TABHERE>wholeStr = preStr+"'+theInterface+'.ice"')
cog.outl('<TABHERE><TABHERE>Ice.loadSlice(wholeStr)')
cog.outl('<TABHERE><TABHERE>ice_'+theInterface+' = True')
cog.outl('<TABHERE><TABHERE>break')
cog.outl('if not ice_'+theInterface+':')
cog.outl("<TABHERE>print('Couldn\\\'t load "+theInterface+"')")
cog.outl('<TABHERE>sys.exit(-1)')
module2 = DSLFactory().from_file(theInterface+'.idsl', includeDirectories=includeDirectories)
cog.outl('from '+ module2['name'] +' import *')
cog.outl('\nclass ' + theInterface+ 'I('+theInterface+'):')
]]]
[[[end]]]
	def __init__(self, worker):
		self.worker = worker

[[[cog

	for interface in module['interfaces']:
		if interface['name'] == theInterface:
			for mname in interface['methods']:
				method = interface['methods'][mname]

				name = method['name']

				paramStrA = ''
				for p in method['params']:
					if p['decorator'] != 'out':
						paramStrA += p['name'] + ', '
				paramStrB = ''
				for p in method['params']:
					if p['decorator'] != 'out':
						if paramStrB == '': delim = ''
						else: delim = ', '
						paramStrB += delim + p['name']


				cog.outl('<TABHERE>def ' + name + '(self, ' + paramStrA + 'c):')
				cog.out('<TABHERE><TABHERE>return self.worker.' + interface['name'] + "_" + name+'(')
				cog.out(paramStrB)
				cog.out(')\n')

]]]
[[[end]]]
