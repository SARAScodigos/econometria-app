import os
import sys
import subprocess
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class ScriptWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, script_path, cwd):
        super().__init__()
        self.script_path = script_path
        self.cwd = cwd

    def run(self):
        self.output_signal.emit(f"--- Ejecutando: {os.path.basename(self.script_path)} ---\n")
        try:
            # Run the python script
            process = subprocess.Popen(
                [sys.executable, self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.output_signal.emit(line)
                    
            process.stdout.close()
            process.wait()
            self.output_signal.emit(f"\n--- Finalizado con código: {process.returncode} ---\n\n")
            self.finished_signal.emit(process.returncode)
        except Exception as e:
            self.output_signal.emit(f"Error al ejecutar el script: {str(e)}\n")
            self.finished_signal.emit(-1)

class MainWindow(QMainWindow):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
        self.core_dir = os.path.join(base_dir, "src", "core")
        self.setWindowTitle("Aplicación Econométrica UDEP")
        self.resize(900, 600)
        self.worker = None

        self._setup_ui()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        
        # Left panel: Buttons
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.buttons = {}
        
        # Group 1: Pruebas y Datos
        group1 = QGroupBox("1. Datos y Pruebas")
        g1_layout = QVBoxLayout()
        self.add_script_button(g1_layout, "Comprobar Estacionalidad", "comprobacion_estacionalidad.py")
        group1.setLayout(g1_layout)
        left_layout.addWidget(group1)
        
        # Group 2: Estimaciones Base
        group2 = QGroupBox("2. Estimaciones y Baseline")
        g2_layout = QVBoxLayout()
        self.add_script_button(g2_layout, "VARX Estimation (Pre-COVID)", "covidshock_estimation.py")
        self.add_script_button(g2_layout, "Baseline Sin COVID", "baseline_sin_covid.py")
        group2.setLayout(g2_layout)
        left_layout.addWidget(group2)
        
        # Group 3: Contrafactuales y Escenarios
        group3 = QGroupBox("3. Escenarios y Contrafactuales")
        g3_layout = QVBoxLayout()
        self.add_script_button(g3_layout, "Contrafactual COVID (VARX)", "calculo_contrafractual_covid.py")
        self.add_script_button(g3_layout, "Escenarios Macro Fin K=2", "escenarios_macro_fin_k2.py")
        self.add_script_button(g3_layout, "Contrafactual Independiente", "contrafractual_independiente.py")
        self.add_script_button(g3_layout, "Contrafactual No Independiente", "contrafractual_no_independiente.py")
        self.add_script_button(g3_layout, "Shock PBI VARX", "shock_pbi_varx.py")
        group3.setLayout(g3_layout)
        left_layout.addWidget(group3)
        
        # Group 4: Gráficos
        group4 = QGroupBox("4. Gráficos")
        g4_layout = QVBoxLayout()
        self.add_script_button(g4_layout, "Plots Variables", "plot_vars.py")
        self.add_script_button(g4_layout, "Plots Escenarios", "plots_escenarios.py")
        self.add_script_button(g4_layout, "Plot Credit Levels Scenarios", "plot_credit_levels_scenarios.py")
        self.add_script_button(g4_layout, "Plot Mora Levels Scenarios", "plot_mora_levels_scenarios.py")
        self.add_script_button(g4_layout, "Plot Credit Growth Bootstrap", "plot_credit_growth_bootstrap.py")
        self.add_script_button(g4_layout, "Plot Mora Growth Bootstrap", "plot_mora_growth_bootstrap.py")
        group4.setLayout(g4_layout)
        left_layout.addWidget(group4)
        
        scroll_left = QScrollArea()
        scroll_left.setWidget(left_panel)
        scroll_left.setWidgetResizable(True)
        scroll_left.setFixedWidth(350)
        
        main_layout.addWidget(scroll_left)
        
        # Right panel: Console Output
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("Consola de Salida:"))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: monospace;")
        right_layout.addWidget(self.console)
        
        clear_btn = QPushButton("Limpiar Consola")
        clear_btn.clicked.connect(self.console.clear)
        right_layout.addWidget(clear_btn)
        
        main_layout.addWidget(right_panel)

    def add_script_button(self, layout, label_text, script_name):
        btn = QPushButton(label_text)
        script_path = os.path.join(self.core_dir, script_name)
        btn.clicked.connect(lambda checked, s=script_path: self.run_script(s))
        layout.addWidget(btn)
        self.buttons[script_name] = btn

    def run_script(self, script_path):
        if self.worker is not None and self.worker.isRunning():
            self.console.append("--- Por favor espera a que termine el script actual ---")
            return
            
        if not os.path.exists(script_path):
            self.console.append(f"Error: No se encontró el script en {script_path}")
            return
            
        self.worker = ScriptWorker(script_path, cwd=self.core_dir)
        self.worker.output_signal.connect(self.append_console)
        self.worker.finished_signal.connect(self.script_finished)
        self.worker.start()

    def append_console(self, text):
        self.console.insertPlainText(text)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def script_finished(self, code):
        pass
