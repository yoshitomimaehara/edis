# -*- coding: utf-8 -*-
# EDIS - Entorno de Desarrollo Integrado Simple para C/C++
#
# This file is part of EDIS
# Copyright 2014 - Gabriel Acosta
# License: GPLv3 (see http://www.gnu.org/licenses/gpl.html)

# Módulos Python
import os
import sys
from re import findall
from subprocess import Popen, PIPE

# Módulos QtGui
from PyQt4.QtGui import (
    QMainWindow,
    QDesktopWidget,
    QToolBar,
    QApplication,
    QMessageBox
    )

# Módulos QtCore
from PyQt4.QtCore import (
    Qt,
    QSize,
    SIGNAL,
    QSettings
    )

# Módulos EDIS
from src import ui
from src import recursos
from src.helpers import configuraciones
from src.ui import actualizaciones
from src.ui.menu import (
    menu_archivo,
    menu_editar,
    menu_ver,
    menu_buscar,
    menu_herramientas,
    menu_ejecucion,
    menu_acerca_de
    )
from src.ui import widget_central
from src.ui.distribuidor import Distribuidor
from src.ui.contenedor_principal import contenedor_principal
from src.ui.contenedor_secundario import contenedor_secundario
from src.ui.lateral_widget import lateral_container
from src.ui.widgets import barra_de_estado
from src.ui.dialogos import dialogo_guardar_archivos


class IDE(QMainWindow):
    """ Aplicación principal """

    instancia = None

    def __new__(cls, *args, **kargs):
        if cls.instancia is None:
            cls.instancia = QMainWindow.__new__(cls, *args, **kargs)
        return cls.instancia

    def __init__(self):
        QMainWindow.__init__(self)
        self.ini = False
        self.setMinimumSize(850, 700)
        self.setWindowTitle(ui.__nombre__)
        self.comprobar_compilador()
        self._cargar_tema()
        get_pantalla = QDesktopWidget().screenGeometry()
        self.posicionar_ventana(get_pantalla)
        self.showMaximized()

        # Distribuidor
        self.distribuidor = Distribuidor()
        # Widget Central
        self.widget_Central = widget_central.WidgetCentral(self)
        self.cargar_ui(self.widget_Central)
        self.setCentralWidget(self.widget_Central)
        # ToolBar
        self.toolbar = ToolBar(self)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.tog = self.toolbar.toggleViewAction()
        self.tog.setText(self.tr("Visible"))
        self.addToolBar(Qt.RightToolBarArea, self.toolbar)

        self.tray = actualizaciones.Actualizacion(self)
        self.tray.show()
        # Barra de estado
        self.barra_de_estado = barra_de_estado.BarraDeEstado(self)
        #self.barra_de_estado.hide()
        self.setStatusBar(self.barra_de_estado)
        # Menu
        menu = self.menuBar()
        archivo = menu.addMenu(self.tr("&Archivo"))
        editar = menu.addMenu(self.tr("&Editar"))
        ver = menu.addMenu(self.trUtf8("&Ver"))
        buscar = menu.addMenu(self.trUtf8("&Buscar"))
        herramientas = menu.addMenu(self.trUtf8("&Herramientas"))
        ejecucion = menu.addMenu(self.trUtf8("E&jecucion"))
        acerca = menu.addMenu(self.tr("Ace&rca de"))
        self._menu_archivo = menu_archivo.MenuArchivo(
            archivo, self.toolbar, self)
        self._menu_editar = menu_editar.MenuEditar(
            editar, self.toolbar, self)
        self._menu_ver = menu_ver.MenuVer(ver, self.toolbar, self)
        self._menu_herramientas = menu_herramientas.MenuHerramientas(
            herramientas, self.toolbar, self)
        self._menu_buscar = menu_buscar.MenuBuscar(buscar, self.toolbar, self)
        self._menu_ejecucion = menu_ejecucion.MenuEjecucion(
            ejecucion, self.toolbar, self)
        self._menu_acerca_de = menu_acerca_de.MenuAcercade(acerca, self)

        self.connect(self.contenedor_principal,
            SIGNAL("recentTabsModified(QStringList)"),
            self._menu_archivo.actualizar_archivos_recientes)
        self.connect(self._menu_archivo, SIGNAL("abrirArchivo(QString)"),
            self.contenedor_principal.abrir_archivo)
        self.connect(self.contenedor_principal,
            SIGNAL("currentTabChanged(QString)"),
            self.lateral.actualizar_simbolos)
        # Método para cargar items en las toolbar
        self.cargar_toolbar()

        # Iniciar distribuidor despues de la interfáz
        #FIXME: arreglar !!
        self.distribuidor.ini_ide(self)
        self.ini = True

    def posicionar_ventana(self, pantalla):
        """ Posiciona la ventana en el centro de la pantalla. """

        tam_ventana = self.geometry()

        self.move((pantalla.width() - tam_ventana.width()) / 2,
                  (pantalla.height() - tam_ventana.height()) / 2)

    def cargar_ui(self, widget_central):
        """ Carga los contenedores. """

        self.contenedor_principal = contenedor_principal.ContenedorMain(self)
        self.contenedor_secundario = \
            contenedor_secundario.ContenedorSecundario(self)
        self.lateral = lateral_container.LateralContainer(self)
        self.connect(self.contenedor_principal, SIGNAL(
            "currentTabChanged(QString)"), self.cambiar_titulo_de_ventana)
        self.connect(self.contenedor_principal, SIGNAL(
            "currentTabChanged(QString)"), self.cambiar_barra_estado)
        self.connect(self.contenedor_principal, SIGNAL("nuevoArchivo()"),
            self.contenedor_principal.agregar_editor)
        self.connect(self.contenedor_principal, SIGNAL("abrirArchivo()"),
            self.contenedor_principal.abrir_archivo)

        widget_central.agregar_contenedor_central(self.contenedor_principal)
        widget_central.agregar_contenedor_bottom(self.contenedor_secundario)
        widget_central.agregar_contenedor_lateral(self.lateral)

        self.connect(self.lateral.symbols_widget,
            SIGNAL("irALinea(int)"), self.distribuidor.ir_a_linea)
        self.connect(self.contenedor_secundario.salida_.output,
            SIGNAL("irALinea(int)"), self.distribuidor.ir_a_linea)
        self.connect(self.contenedor_principal, SIGNAL(
            "actualizarSimbolos(QString)"), self.lateral.actualizar_simbolos)
        self.connect(self.contenedor_principal, SIGNAL(
            "cursorPositionChanged(int, int)"), self._linea_columna)
        #FIXME: quitar función lambda
        self.connect(self.lateral.file_navigator, SIGNAL("cambioPes(int)"),
            lambda i: self.contenedor_principal.tab.setCurrentIndex(i))
        self.connect(self.lateral.file_explorer,
            SIGNAL("dobleClickArchivo(QString)"),
            lambda f: self.contenedor_principal.abrir_archivo(f))

    def cargar_toolbar(self):
        self.toolbar.clear()
        items = {}

        items.update(self._menu_archivo.items_toolbar)
        #items.update(self._menu_editar.items_toolbar)
        #items.update(self._menu_buscar.items_toolbar)
        #items.update(self._menu_ver.items_toolbar)
        #items.update(self._menu_herramientas.items_toolbar)
        items.update(self._menu_ejecucion.items_toolbar)
        for i in configuraciones.BARRA_HERRAMIENTAS_ITEMS:
            if i == 'separador':
                self.toolbar.addSeparator()
            else:
                item = items.get(i, None)
                if item is not None:
                    self.toolbar.addWidget(item)

    def cargar_status_tips(self, accion, texto):
        accion.setStatusTip(texto)

    def cambiar_barra_estado(self, archivo):
        self.barra_de_estado.nombre_archivo.cambiar_texto(archivo)

    def cambiar_titulo_de_ventana(self, titulo):
        """ Cambia el título cuando la pestaña cambia de nombre """

        if titulo == ui.__nombre__:
            titulo = ""
            return

        nombre_con_extension = os.path.basename(str(titulo)).split('/')[0]
        self.setWindowTitle(nombre_con_extension + ' - ' + ui.__nombre__)

    def _linea_columna(self):
        """ Muestra el número de línea y columna del archivo actual. """

        editor = self.contenedor_principal.devolver_editor_actual()
        if editor is not None:
            linea, columna = editor.devolver_posicion_del_cursor()
            total_lineas = editor.lineas
            self.barra_de_estado.estado_cursor.actualizar_posicion_cursor(
                linea, total_lineas, columna)

    def keyPressEvent(self, evento):
        pass

    def closeEvent(self, evento):
        """ Al cerrar EDIS se comprueba archivos no guardados y se guardan
        las configuraciones. """

        if self.contenedor_principal.check_tabs_sin_guardar() and \
        configuraciones.CONFIRMAR_AL_CERRAR:
            archivos_sin_guardar = \
                self.contenedor_principal.devolver_archivos_sin_guardar()
            dialogo = dialogo_guardar_archivos.Dialogo(archivos_sin_guardar)
            dialogo.exec_()
            if dialogo.ignorado():
                evento.ignore()
        self.guardar_configuraciones()

    def _cargar_tema(self):
        """ Carga el tema por defecto """

        with open(recursos.TEMA_POR_DEFECTO) as q:
            tema = q.read()
        QApplication.instance().setStyleSheet(tema)

    def cargar_sesion(self, archivosPrincipales, archivos_recientes=None):
        """ Carga archivos desde la última sesión. """

        self.contenedor_principal.abrir_archivos(archivosPrincipales)
        if archivos_recientes:
            self._menu_archivo.actualizar_archivos_recientes(archivos_recientes)

    def comprobar_compilador(self):
        """ Antes de cargar la interfáz de EDIS se comprueba si GCC está
        presente en el sistema. """

        #FIXME: Change this!!!
        sistema = sys.platform
        execs = {'Win': True if not sistema else False}
        discos_win = findall(r'(\w:)\\',
            Popen('fsutil fsinfo drives', stdout=PIPE).communicate()[0]) if \
                execs['Win'] else None
        progs = ['gcc']
        progs = [progs] if isinstance(progs, str) else progs
        for prog in progs:
            if execs['Win']:  # Comprobación en Windows
                win_cmds = ['dir /B /S {0}\*{1}.exe'.format(letter, prog) for
                            letter in discos_win]
                for cmd in win_cmds:
                    execs[prog] = (Popen(cmd, stdout=PIPE,
                    stderr=PIPE, shell=1).communicate()[0].split(os.linesep)[0])
                    if execs[prog]:
                        break
            else:
                try:  # Comprobación en Linux
                    Popen([prog, '--help'], stdout=PIPE, stderr=PIPE)
                except OSError:
                    SI = QMessageBox.Yes
                    NO = QMessageBox.No
                    r = QMessageBox.question(self, self.trUtf8("Advertencia!"),
                        self.trUtf8("El compilador GCC no está instalado!\n\n"
                        "Instalar?"), SI | NO)
                    if r == SI:
                        #FIXME: Revisar!!
                        instalador = recursos.INSTALADOR
                        Popen(instalador)

    def guardar_configuraciones(self):
        qconfig = QSettings(recursos.CONFIGURACION, QSettings.IniFormat)
        archivosAbiertos_ = self.contenedor_principal.get_documentos_abiertos()
        if qconfig.value('configuraciones/general/cargarArchivos',
            True).toBool():
                qconfig.setValue('archivosAbiertos/mainTab',
                    archivosAbiertos_[0])
                qconfig.setValue('archivosAbiertos/archivosRecientes',
                    self.contenedor_principal.tab.get_archivos_recientes)


class ToolBar(QToolBar):

    def __init__(self, parent=None):
        QToolBar.__init__(self, parent)
        self.setMovable(False)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setIconSize(QSize(30, 30))