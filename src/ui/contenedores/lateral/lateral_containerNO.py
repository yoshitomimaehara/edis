# -*- coding: utf-8 -*-
# EDIS - a simple cross-platform IDE for C
#
# This file is part of EDIS
# Copyright 2014-2015 - Gabriel Acosta
# License: GPLv3 (see http://www.gnu.org/licenses/gpl.html)

from PyQt4.QtGui import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QStackedWidget,
    QSplitter
    )

from PyQt4.QtCore import (
    SIGNAL,
    Qt
    )

from src.helpers.configuracion import ESettings
from src.ui.contenedores.lateral import (
    navegador,
    arbol_simbolos,
    explorador
    )
from src.ectags import ectags


class ContenedorLateral(QWidget):

    def __init__(self, parent=None):
        super(ContenedorLateral, self).__init__()
        self._edis = parent
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        # Splitter
        self._splitter_principal = QSplitter(Qt.Vertical)
        self._splitter_principal.setObjectName("split_lateral")
        self._splitter_secundario = QSplitter(Qt.Vertical)

        self.stack = Stacked(self._edis)
        self._splitter_principal.addWidget(self.stack)

        # Navegador
        self._navegador = navegador.Navegador()
        self.connect(self._edis.contenedor_editor,
                     SIGNAL("archivo_abierto(QString)"),
                     self._navegador.agregar)
        self.connect(self._edis.contenedor_editor,
                     SIGNAL("archivo_cerrado(int)"),
                     self._navegador.eliminar)
        self.connect(self._edis.contenedor_editor,
                     SIGNAL("cambiar_item(int)"),
                    self._navegador.cambiar_foco)
        self.connect(self._navegador,
                     SIGNAL("cambiar_editor(int)"),
                     self._edis.contenedor_editor.cambiar_widget)

        self._splitter_secundario.addWidget(self._navegador)
        self._splitter_principal.addWidget(self._splitter_secundario)
        box.addWidget(self._splitter_principal)

    def actualizar_simbolos(self, archivo):
        self.stack.actualizar_simbolos(archivo)


class Stacked(QWidget):

    def __init__(self, parent=None):
        super(Stacked, self).__init__()
        #FIXME:
        self.ctags = ectags.Ctags()
        self._edis = parent
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)

        # Combo selector
        self.combo_selector = QComboBox()
        self.combo_selector.setObjectName("combo_selector")
        box.addWidget(self.combo_selector)

        # Stacked
        self.stack = QStackedWidget()
        box.addWidget(self.stack)

        # Widgets
        self._arbol_simbolos = None
        if ESettings.get('gui/simbolos'):
            self.agregar_arbol_de_simbolos()
        self._explorador = None
        if ESettings.get('gui/explorador'):
            self.agregar_explorador()

        #FIXME
        #self.actualizar()

        # Conexiónes
        self.combo_selector.currentIndexChanged[int].connect(
            lambda: self._cambiar_widget(self.combo_selector.currentIndex()))

    def actualizar(self):
        central = self._edis.central
        if self.stack.count() == 0:
            central.splitter_secundario.hide()
        else:
            central.splitter_secundario.show()

    def agregar_arbol_de_simbolos(self):
        if self._arbol_simbolos is None:
            self._arbol_simbolos = arbol_simbolos.ArbolDeSimbolos()
            self.combo_selector.addItem(self.tr("Símbolos"))
            self.stack.addWidget(self._arbol_simbolos)

    def agregar_explorador(self):
        if self._explorador is None:
            self._explorador = explorador.Explorador()
            self.combo_selector.addItem(self.tr("Explorador"))
            self.stack.addWidget(self._explorador)

            self.connect(self._explorador, SIGNAL("abriendoArchivo(QString)"),
                         self._edis.contenedor_editor.abrir_archivo)

    #def eliminar_arbol_de_simbolos(self):
        #if self._arbol_simbolos is not None:
            #indice = self.stack.indexOf(self._arbol_simbolos)
            #self.stack.removeWidget(self._arbol_simbolos)
            #self.combo_selector.removeItem(indice)
            #self._arbol_simbolos = None

    #def eliminar_navegador(self):
        #if self._navegador is not None:
            #indice = self.stack.indexOf(self._navegador)
            #self.stack.removeWidget(self._navegador)
            #self.combo_selector.removeItem(indice)
            #self._navegador = None

    #def eliminar_explorador(self):
        #if self._explorador is not None:
            #indice = self.stack.indexOf(self._explorador)
            #self.stack.removeWidget(self._explorador)
            #self.combo_selector.removeItem(indice)
            #self._explorador = None

    def _cambiar_widget(self, indice):
        self.stack.setCurrentIndex(indice)

    def actualizar_simbolos(self, archivo):
        if archivo == 'Nuevo_archivo':
            return
        tag = self.ctags.run_ctags(archivo)
        simbolos = self.ctags.parser(tag)
        self._arbol_simbolos.actualizar_simbolos(simbolos)