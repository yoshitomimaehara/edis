#-*- coding: utf-8 -*-

"""
Configuraciones

"""
import sys

from PyQt4.QtCore import QSettings

from side_c import recursos

###############################################################################
#                        MÁRGEN                                               #
###############################################################################
MARGEN = 80
MOSTRAR_MARGEN = True

###############################################################################
#                   SISTEMA OPERATIVO                                         #
###############################################################################
SISTEMA_OPERATIVO = sys.platform
WIN = 'win32'
TUX = 'linux2'

if SISTEMA_OPERATIVO == WIN:
    FUENTE = 'Courier'
    TAM_FUENTE = 10
    WINDOWS = True
    LINUX = False
else:
    FUENTE = 'Monospace'
    TAM_FUENTE = 11
    LINUX = True
    WINDOWS = False

FUENTE_MAX_TAM = 80
FUENTE_MIN_TAM = 6

INDENTACION = 4
###############################################################################
#                   CONFIGURACIONES                                           #
###############################################################################
qsettings = QSettings(recursos.CONFIGURACIONES_PATH, QSettings.IniFormat)

MARGEN = qsettings.value('configuraciones/editor/margenLinea', 80, type=int)
MOSTRAR_MARGEN = qsettings.value(
    'configuraciones/editor/mostrarMargen', True, type=bool)
fuente_f = qsettings.value('configuraciones/editor/fuente', "", type='QString')
if fuente_f:
    FUENTE = fuente_f
fuente_tam = qsettings.value('configuraciones/editor/fuenteTam', 0, type=int)
if fuente_tam != 0:
    TAM_FUENTE = fuente_tam
INDENTACION = qsettings.value('configuraciones/editor/indentacion', 4, type=int)