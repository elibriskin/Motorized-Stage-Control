import numpy as np
import pandas as pd
import random
import sys
import qdarkstyle
import qdarktheme
import serial
import pyfirmata
from Actuator import Actuator

from PyQt6.QtWidgets import (
    QMainWindow, QApplication,
    QLabel, QDialog, QToolBar, QStatusBar,
    QPushButton, QDialogButtonBox,
    QFormLayout, QDoubleSpinBox, QMessageBox,
    QCheckBox, QFileDialog, QComboBox, QVBoxLayout, QHBoxLayout,
    QTabWidget, QWidget, QGroupBox, QCheckBox, QGridLayout
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QSize, QStringListModel, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import pyqtgraph as pg
# from PowerMeter import PowerMeter

pg.setConfigOption('background', (255,255,255, 0))

address = "COM9"
board = pyfirmata.Arduino(address)

actuator1 = Actuator(board=board, in1=2, in2=3)
actuator2 = Actuator(board=board, in1=4, in2=5)
actuator3 = Actuator(board=board, in1=12, in2=13)

def readValue(serialPort):
    return(ord(serialPort.read(1)))

def get_voltage(serialPort):
    newValue = readValue(serialPort)
    voltage = (newValue / 1024) * 5
    return voltage


#Plot Object
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=2, height=4, dpi=0):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class MainPlot():
    def __init__(self):
        self.plot_graph = pg.PlotWidget()
        pen = pg.mkPen(color=(255, 255, 255))
        self.plot_graph.setTitle("Optical Power Monitor", size="12pt")
        styles = {"color": "white", "font-size": "14px", "font-weight": "light"}
        self.plot_graph.setLabel("left", "Optical Power (W)", **styles)
        self.plot_graph.addLegend()
        self.plot_graph.showGrid(x=True, y=True)
        self.voltage_level = 5
        self.n = 1000
        self.time = list(range(self.n))
        self.voltage = [0 for _ in range(self.n)]

        # Get a line reference
        self.line = self.plot_graph.plot(
            self.time,
            self.voltage,
            name="Optical Power Read (W)",
            pen=pen
        )

    def update_plot(self):
        self.time = self.time[1:]
        self.time.append(self.time[-1] + 1)
        self.voltage = self.voltage[1:]
        voltage = get_voltage(serialPort)
        self.voltage.append(voltage)
        self.line.setData(self.time, self.voltage)

class PowerPlot():
    def __init__(self):
        self.plot_graph = pg.PlotWidget()
        pen = pg.mkPen(color=(255, 0, 0))
        self.plot_graph.setTitle("Power Log", size="12pt")
        styles = {"color": "white", "font-size": "14px", "font-weight": "light"}
        self.plot_graph.setLabel("left", "Optical Power (W)", **styles)
        self.plot_graph.addLegend()
        self.plot_graph.showGrid(x=True, y=True)
        self.n = 10
        self.plot_index = 0
        self.time = list(range(self.n))
        self.power = [0 for _ in range(self.n)]
        self.line = self.plot_graph.plot(
            self.time,
            self.power,
            name="Optical Power Read (W)",
            pen=pen,
            symbol='o'
        )

    def update_plot(self):
        if self.plot_index >= 9:
            self.time = self.time[1:]
            self.time.append(self.time[-1] + 1)
            self.power = self.power[1:]
            self.power.append(power_meter.get_power())
        else:
            self.power[self.plot_index] = float(power_meter.get_power())
        self.line.setData(self.time, self.power)
        self.plot_index += 1



class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #Internal attributes
        self.stage_routine = None

        #Window Attributes
        self.setWindowTitle("Main Window")
        # self.setFixedSize(QSize(800, 500))

        #Window Plotting Canvas
        self.canvas = MplCanvas(self, width=5, height=4, dpi=10)
        self.initialize_canvas = True

        #Toolbar
        toolbar = QToolBar("Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        #Toolbar Buttons

        #Toggle
        toggle_button = QAction(QIcon("icons/chart-histogram.png"), "Toggle", self)
        toggle_button.setStatusTip("Toggle Button")
        toggle_button.triggered.connect(self.toggle)
        toolbar.addAction(toggle_button)

        #Adjust voltage
        routine_button = QAction(QIcon("icons/settings-sliders.png"), "Run Stage Routine", self)
        routine_button.setStatusTip("Run Routine")
        routine_button.triggered.connect(self.run_routine)
        toolbar.addAction(routine_button)

        # Reset button
        reset_button = QAction(QIcon("icons/settings.png"), "Reset Stages", self)
        reset_button.setStatusTip("Reset Button")
        reset_button.triggered.connect(self.reset)
        toolbar.addAction(reset_button)

        #Menu
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        edit_menu = menu.addMenu("&Edit")
        view_menu = menu.addMenu("&View")

        #Menu Options

        # Stage Routine Options
        stage_routine = QAction("&Set Stage Routine...", self)
        stage_routine.triggered.connect(self.create_stage_routine)
        file_menu.addAction(stage_routine)

        # Voltage Menu
        voltage_adjust_option = QAction("&Adjust Voltage...", self)
        voltage_adjust_option.triggered.connect(self.voltage_window)
        file_menu.addAction(voltage_adjust_option)

        #Main Panel Settings
        self.main_panel = QWidget()
        self.main_panel_layout = QHBoxLayout()
        self.setCentralWidget(self.main_panel)

        #Control Panel
        self.control_panel = QGroupBox("Optical Meter Control")
        self.control_panel_layout = QGridLayout()

        #Control Panel Inputs

        #Set up panel for stage 1
        self.stage1_panel = QGroupBox("Stage 1")
        self.stage1_panel_layout = QGridLayout()

        #Set up inputs for controlling stage 1
        self.stage1_input = QDoubleSpinBox(minimum=-30, maximum=30, singleStep=0.01, value=0)
        self.stage1_button = QPushButton("Set")
        self.stage1_button.clicked.connect(self.move_stage1)
        self.stage1_position_label = QLabel("Current position: 0mm")
        self.stage1_reference_button = QPushButton("Set Reference")

        #Add inputs to stage 1 panel
        self.stage1_panel_layout.addWidget(self.stage1_input, 0, 0)
        self.stage1_panel_layout.addWidget(self.stage1_button, 0, 1)
        self.stage1_panel_layout.addWidget(self.stage1_position_label, 1, 0)
        self.stage1_panel_layout.addWidget(self.stage1_reference_button, 1, 1)

        #Set layout of stage 1 panel
        self.stage1_panel.setLayout(self.stage1_panel_layout)

        #Set up panel for stage 2
        self.stage2_panel = QGroupBox("Stage 2")
        self.stage2_panel_layout = QGridLayout()

        #Set up inputs for controlling stage 2
        self.stage2_input = QDoubleSpinBox(minimum=-30, maximum=30, singleStep=0.01, value=0)
        self.stage2_button = QPushButton("Set")
        self.stage2_button.clicked.connect(self.move_stage2)
        self.stage2_position_label = QLabel("Current position: 0mm")
        self.stage2_reference_button = QPushButton("Set Reference")

        #Add inputs to stage 2 panel
        self.stage2_panel_layout.addWidget(self.stage2_input, 0, 0)
        self.stage2_panel_layout.addWidget(self.stage2_button, 0, 1)
        self.stage2_panel_layout.addWidget(self.stage2_position_label, 1, 0)
        self.stage2_panel_layout.addWidget(self.stage2_reference_button, 1, 1)

        #Set layout of stage 2 panel
        self.stage2_panel.setLayout(self.stage2_panel_layout)

        #Set up panel for stage 3
        self.stage3_panel = QGroupBox("Stage 3")
        self.stage3_panel_layout = QGridLayout()

        #Set up inputs for controlling stage 1
        self.stage3_input = QDoubleSpinBox(minimum=-30, maximum=30, singleStep=0.01, value=0)
        self.stage3_button = QPushButton("Set")
        self.stage3_button.clicked.connect(self.move_stage3)
        self.stage3_position_label = QLabel("Current position: 0mm")
        self.stage3_reference_button = QPushButton("Set Reference")

        #Add inputs to stage 3 panel
        self.stage3_panel_layout.addWidget(self.stage3_input, 0, 0)
        self.stage3_panel_layout.addWidget(self.stage3_button, 0, 1)
        self.stage3_panel_layout.addWidget(self.stage3_position_label, 1, 0)
        self.stage3_panel_layout.addWidget(self.stage3_reference_button, 1, 1)

        #Set layout of stage 3 panel
        self.stage3_panel.setLayout(self.stage3_panel_layout)

        #Set plot updating and measurement options
        self.plot_toggle = QCheckBox("Monitor")
        self.plot_toggle.clicked.connect(self.toggle)
        self.record_power_button = QPushButton("Record Power")
        self.record_power_button.clicked.connect(self.update_power_plot)

        #Set up window layout
        self.control_panel_layout.addWidget(self.stage1_panel, 0, 0, 1, 2)
        self.control_panel_layout.addWidget(self.stage2_panel, 1, 0, 1, 2)
        self.control_panel_layout.addWidget(self.stage3_panel, 2, 0, 1, 2)
        self.control_panel_layout.addWidget(self.plot_toggle, 3, 0, 1, 1)
        self.control_panel_layout.addWidget(self.record_power_button, 3, 1, 1, 1)

        self.control_panel.setLayout(self.control_panel_layout)

        #Plotting
        self.toggle_plot = False
        self._plot_ref = None
        self.canvas.draw()

        #Main Panel Layout
        self.tab_window = MyTabWidget()
        self.main_panel_layout.addWidget(self.control_panel, 1)
        self.main_panel_layout.addWidget(self.tab_window, 2,)

        self.main_panel.setLayout(self.main_panel_layout)

        #Update Plot Timer
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.tab_window.main_plot.update_plot)

    #Stage functions

    def move_stage1(self):
        '''
        Moves optical stage 1.
        '''

        #Stage 1 moving distance
        distance = self.stage1_input.value()

        #Move the stage
        actuator1.move(distance)

        #Set position reference
        self.stage1_position_label.setText(f"Current position: {actuator1.reference}mm")

    def move_stage2(self):
        '''
        Moves optical stage 1.
        '''

        #Stage 1 moving distance
        distance = self.stage2_input.value()

        #Move the stage
        actuator2.move(distance)

        #Set position reference
        self.stage2_position_label.setText(f"Current position: {actuator2.reference}mm")

    def move_stage3(self):
        '''
        Moves optical stage 1.
        '''

        #Stage 1 moving distance
        distance = self.stage3_input.value()

        #Move the stage
        actuator3.move(distance)

        #Set position reference
        self.stage3_position_label.setText(f"Current position: {actuator3.reference}mm")

    def run_routine(self):
        '''
        Runs a sequence of stage movements.
        '''

        #Dictionary of actuators
        actuators = {
            "Actuator 1": actuator1,
            "Actuator 2": actuator2,
            "Actuator 3": actuator3
        }

        if self.stage_routine == None:
            error_menu = ErrorMenu("Stage Routine not Set!")
            error_menu.exec()
        else:
            #For each sequence movement, move corresponding actuator
            for sequence in self.stage_routine:

                #Get specific actuator
                actuator = list(sequence.keys())[0]

                #Move actuator specified number of steps in sequence
                actuators[actuator].move(sequence[actuator])



    def reset(self):
        '''
        Resets all actuators to starting position
        '''
        #Reset actuators and update references

        actuator1.reset()
        self.stage1_position_label.setText(f"Current position: {actuator1.reference}mm")

        actuator2.reset()
        self.stage2_position_label.setText(f"Current position: {actuator2.reference}mm")

        actuator3.reset()
        self.stage3_position_label.setText(f"Current position: {actuator3.reference}mm")
    
    
    #Window Functions

    def create_stage_routine(self):
        '''
        Creates and sets a series of stage movements in a routine.
        '''
        menu = StageRoutineMenu()
        if menu.exec():
            self.stage_routine = menu.stage_routine

    def voltage_window(self):
        menu = VoltageMenu()
        if menu.exec():
            self.main_plot.voltage_level = menu.voltage_input.value()

    def toggle(self):
        '''
        Toggles measurement plot
        '''
        self.toggle_plot = not self.toggle_plot
        self.update_plot()

    def update_plot(self):
        '''
        Updates measurement plot.
        '''
        if self.toggle_plot == True:
            self.timer.start()
        else:
            self.timer.stop()

    def update_power_plot(self):
        self.tab_window.power_plot.update_plot()

class StageRoutineMenu(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Create Stage Routine...")

        self.sequence_index = 7
        self.stage_routine = []

        #Window Buttons
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.button_box = QDialogButtonBox(QBtn)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        #Menu Input

        #Set up movement options for each actuator
        self.actuator1_label = QLabel("Actuator 1")
        self.actuator1_steps = QDoubleSpinBox(minimum=-30, maximum=30, value=15)
        self.actuator1_button = QPushButton("Add")
        self.actuator1_button.clicked.connect(self.add_actuator1_sequence)

        self.actuator2_label = QLabel("Actuator 2")
        self.actuator2_steps = QDoubleSpinBox(minimum=-30, maximum=30, value=15)
        self.actuator2_button = QPushButton("Add")
        self.actuator2_button.clicked.connect(self.add_actuator2_sequence)

        self.actuator3_label = QLabel("Actuator 3")
        self.actuator3_steps = QDoubleSpinBox(minimum=-30, maximum=30, value=15)
        self.actuator3_button = QPushButton("Add")
        self.actuator3_button.clicked.connect(self.add_actuator3_sequence)

        #Set up time delay options
        self.time_step = QDoubleSpinBox(minimum=0, maximum = 1000, value=1)
        self.time_step_label = QLabel("Time Between Each Step: ")
        self.time_routine = QDoubleSpinBox(minimum=0, maximum = 1000, value=1)
        self.time_routine_label = QLabel("Time Between Each Sequence ")

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_routine)


        #Window Layout
        self.layout = QGridLayout()

        #Add Inputs
        self.layout.addWidget(self.actuator1_label, 0, 0, 1, 1)
        self.layout.addWidget(self.actuator1_steps, 0, 1, 1, 2)
        self.layout.addWidget(self.actuator1_button, 0, 3, 1, 1)

        self.layout.addWidget(self.actuator2_label, 1, 0, 1, 1)
        self.layout.addWidget(self.actuator2_steps, 1, 1, 1, 2)
        self.layout.addWidget(self.actuator2_button, 1, 3, 1, 1)

        self.layout.addWidget(self.actuator3_label, 2, 0, 1, 1)
        self.layout.addWidget(self.actuator3_steps, 2, 1, 1, 2)
        self.layout.addWidget(self.actuator3_button, 2, 3, 1, 1)

        self.layout.addWidget(self.time_step_label, 3, 0, 1, 1)
        self.layout.addWidget(self.time_step, 3, 1, 1, 2)
        self.layout.addWidget(self.time_routine_label, 4, 0, 1, 1)
        self.layout.addWidget(self.time_routine, 4, 1, 1, 2)

        self.layout.addWidget(self.clear_button, 5, 0)

        self.layout.addWidget(self.button_box, 5, 1, 1, 3)
        self.setLayout(self.layout)

    def add_actuator1_sequence(self):
        steps = self.actuator1_steps.value()
        sequence_label = QLabel(f"Actuator 1: {steps} steps")
        self.layout.addWidget(sequence_label, self.sequence_index, 0)
        self.sequence_index += 1
        self.stage_routine.append({
            "Actuator 1": steps
        })

    def add_actuator2_sequence(self):
        steps = self.actuator2_steps.value()
        sequence_label = QLabel(f"Actuator 2: {steps} steps")
        self.layout.addWidget(sequence_label, self.sequence_index, 0)
        self.sequence_index += 1
        self.stage_routine.append({
            "Actuator 2": steps
        })

    def add_actuator3_sequence(self):
        steps = self.actuator3_steps.value()
        sequence_label = QLabel(f"Actuator 3: {steps} steps")
        self.layout.addWidget(sequence_label, self.sequence_index, 0)
        self.sequence_index += 1
        self.stage_routine.append({
            "Actuator 3": steps
        })

    def clear_routine(self):
        for i in reversed(range(15, self.layout.count())): 
            self.layout.itemAt(i).widget().deleteLater()
        self.stage_routine = []

class ErrorMenu(QDialog):
    '''
    This is an all-purpose error menu, mostly used for validation issues.
    '''
    def __init__(self, message):
        super().__init__()

        self.setWindowTitle("ERROR!")

        QBtn = QDialogButtonBox.StandardButton.Ok
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        self.message = message
        error_message = QLabel(self.message)
        self.layout.addWidget(error_message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
            

class VoltageMenu(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Assign Voltage Signal")

        #Window Buttons
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.button_box = QDialogButtonBox(QBtn)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        #Numeric Input
        self.voltage_input = QDoubleSpinBox()

        #Window Layout
        self.layout = QFormLayout()

        #Add Inputs
        self.layout.addRow("Assign Output Voltage: ", self.voltage_input)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)


class MyTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super(MyTabWidget, self).__init__(parent)
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        # Plotting Data
        self.main_plot = MainPlot()
        self.power_plot = PowerPlot()

        self.addTab(self.tab1, "Optical Monitor")
        self.addTab(self.tab2, "Power Log")

        self.tab1.layout = QVBoxLayout()
        self.tab1.layout.addWidget(self.main_plot.plot_graph)
        self.tab1.setLayout(self.tab1.layout)

        self.tab2.layout = QVBoxLayout()
        self.tab2.layout.addWidget(self.power_plot.plot_graph)
        self.tab2.setLayout(self.tab2.layout)

def app_run():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarktheme.load_stylesheet('dark'))
    window=MainWindow()
    window.show()
    app.exec()
    board.exit()

sys.exit(app_run())