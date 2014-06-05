#-*- coding: utf-8 -*-

from PyQt4.QtGui import QMainWindow
from PyQt4.QtGui import QDesktopWidget
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QToolBar
from PyQt4.QtGui import QApplication
from PyQt4.QtGui import QLabel

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QSize

from side_c.interfaz.menu import menu_archivo
from side_c.interfaz.menu import menu_editar
from side_c.interfaz.menu import menu_ver
from side_c.interfaz.menu import menu_insertar
from side_c.interfaz.menu import menu_buscar
from side_c.interfaz.menu import menu_codigo
from side_c.interfaz.menu import menu_acerca_de

from side_c.interfaz import widget_central
from side_c.interfaz.contenedor_principal import contenedor_principal
from side_c.interfaz.contenedor_secundario import contenedor_secundario

from side_c import recursos
from side_c.nucleo import configuraciones


ITEMS_TOOLBAR1 = [
    "separador",
    "nuevo-archivo",
    "abrir-archivo",
    "guardar-archivo",
    "guardar-como-archivo",
    "separador",
    "compilar-archivo",
    "ejecutar-archivo",
    "compilar_ejecutar-archivo",
    "separador"
    ]

ITEMS_TOOLBAR2 = [
    "separador",
    "deshacer",
    "rehacer",
    "separador",
    "cortar",
    "copiar",
    "pegar",
    "separador",
    "titulo",
    "linea",
    "separador"
    ]

__instanciaIde = None


# Singleton
def IDE(*args, **kw):
    global __instanciaIde
    if __instanciaIde is None:
        __instanciaIde = __IDE(*args, **kw)
    return __instanciaIde


class __IDE(QMainWindow):
    """ Aplicación principal """

    def __init__(self):
        QMainWindow.__init__(self)
        self.setMinimumSize(850, 700)
        self.setWindowTitle('SIDE-C - Version: 0.x DEV')
        self._cargar_tema()
        get_pantalla = QDesktopWidget().screenGeometry()
        self.posicionar_ventana(get_pantalla)
        self.setWindowIcon(QIcon(recursos.ICONOS['icono']))
        self.showMaximized()
         # Barra de estado
        self.barra_de_estado = self.statusBar()
        label = QLabel(self.tr("SIDE-C | version DEV"))
        self.barra_de_estado.addWidget(label)
        #self.barra_de_estado.hide()
        self.barra_de_estado.show()

        self.widget_Central = widget_central.WidgetCentral(self)
        self.cargar_ui(self.widget_Central)
        self.setCentralWidget(self.widget_Central)

        # ToolBar
        self.toolbar = QToolBar(self)
        self.toolbar_ = QToolBar(self)
        if not configuraciones.LINUX:
            self.toolbar_.setIconSize(QSize(30, 30))
            self.toolbar.setIconSize(QSize(30, 30))
        else:
            self.toolbar_.setIconSize(QSize(20, 20))
            self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar_)
        self.addToolBar(Qt.RightToolBarArea, self.toolbar)

        # Menu
        menu = self.menuBar()
        archivo = menu.addMenu(self.tr("&Archivo"))
        editar = menu.addMenu(self.tr("&Editar"))
        ver = menu.addMenu(self.trUtf8("&Ver"))
        insertar = menu.addMenu(self.trUtf8("&Insertar"))
        buscar = menu.addMenu(self.trUtf8("&Buscar"))
        codigo = menu.addMenu(self.trUtf8("&Codigo fuente"))
        acerca = menu.addMenu(self.tr("Ace&rca de"))

        self._menu_archivo = menu_archivo.MenuArchivo(
            archivo, self.toolbar, self)
        self._menu_editar = menu_editar.MenuEditar(
            editar, self.toolbar_, self)
        self._menu_ver = menu_ver.MenuVer(ver, self)
        self._menu_insertar = menu_insertar.MenuInsertar(
            insertar, self.toolbar_, self)
        self._menu_buscar = menu_buscar.MenuBuscar(buscar, self)
        self._menu_codigo = menu_codigo.MenuCodigoFuente(
            codigo, self.toolbar, self)
        self._menu_acerca_de = menu_acerca_de.MenuAcercade(acerca, self)

        # Métodos para cargar items en las toolbar
        self.cargar_toolbar([self._menu_archivo, self._menu_codigo],
                            self.toolbar,
                            ITEMS_TOOLBAR1)

        self.cargar_toolbar([self._menu_editar, self._menu_insertar],
                            self.toolbar_,
                            ITEMS_TOOLBAR2)

    def posicionar_ventana(self, pantalla):
        """ Posiciona la ventana en el centro de la pantalla. """

        tam_ventana = self.geometry()

        self.move((pantalla.width() - tam_ventana.width()) / 2,
                  (pantalla.height() - tam_ventana.height()) / 2)

    def cargar_ui(self, widget_central):
        self.contenedor_principal = contenedor_principal.ContenedorMain(self)
        self.contenedor_secundario = \
            contenedor_secundario.ContenedorBottom(self)

        widget_central.agregar_contenedor_central(self.contenedor_principal)
        widget_central.agregar_contenedor_bottom(self.contenedor_secundario)

    def cargar_toolbar(self, menus, toolbar, items):
        """ Carga los items en el toolbar
            menus: lista de menus o menu.
            toolbar: QToolBar
            items: lista de items
        """
        toolbar.clear()
        items_toolbar = {}

        if isinstance(menus, list):
            for menu in menus:
                items_toolbar.update(menu.items_toolbar)
        else:
            items_toolbar.update(menus.items_toolbar)

        for item in items:
            if item == 'separador':
                toolbar.addSeparator()
            else:
                item_tool = items_toolbar.get(item, None)

                if item_tool is not None:
                    toolbar.addAction(item_tool)

    def _cargar_tema(self):
        """ Carga el tema por defecto """

        qss = recursos.TEMA_POR_DEFECTO
        #qss = recursos.TEMA_BLACK_SIDE
        with open(qss) as q:
            tema = q.read()
        QApplication.instance().setStyleSheet(tema)