from PyQt5.QtWidgets import (QMainWindow, QTextEdit, QStatusBar, QVBoxLayout, QWidget, 
                            QHBoxLayout, QLabel, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSlot
import logging

class ModuleFilter(logging.Filter):
    def __init__(self, allowed_modules):
        super().__init__()
        self.allowed_modules = allowed_modules

    def filter(self, record):
        return record.module in self.allowed_modules

class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.setStyleSheet("background-color: black; color: white; font-family: Consolas;")

    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)
        # Scroll to bottom
        self.widget.verticalScrollBar().setValue(self.widget.verticalScrollBar().maximum())

class LogWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trading Secretary V2")
        self.setGeometry(100, 100, 1200, 600)  # Increased width for two panels
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create progress bar section
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        
        # Add progress label
        self.progress_label = QLabel("Trading Progress: 0/0")
        self.progress_label.setStyleSheet("color: white; font-weight: bold;")
        progress_layout.addWidget(self.progress_label)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2c3e50;
                border-radius: 5px;
                text-align: center;
                color: white;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_widget)
        
        # Create horizontal layout for two log panels
        h_layout = QHBoxLayout()
        main_layout.addLayout(h_layout)
        
        # Left panel for trading logs
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_label = QLabel("Trading Logs")
        left_label.setStyleSheet("color: white; background-color: #2c3e50; padding: 5px;")
        left_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(left_label)
        
        self.trading_log_widget = QTextEditLogger(self)
        left_layout.addWidget(self.trading_log_widget.widget)
        h_layout.addWidget(left_panel)
        
        # Right panel for Kiwoom logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_label = QLabel("Kiwoom Logs")
        right_label.setStyleSheet("color: white; background-color: #2c3e50; padding: 5px;")
        right_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_label)
        
        self.kiwoom_log_widget = QTextEditLogger(self)
        right_layout.addWidget(self.kiwoom_log_widget.widget)
        h_layout.addWidget(right_panel)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Configure loggers with simplified format
        trading_formatter = logging.Formatter('%(asctime)s > %(message)s', '%H:%M:%S')
        kiwoom_formatter = logging.Formatter('%(asctime)s > %(message)s', '%H:%M:%S')
        
        # Trading logger setup
        self.trading_log_widget.setFormatter(trading_formatter)
        trading_filter = ModuleFilter(['trading_core', 'main', 'trading_strategy'])
        self.trading_log_widget.addFilter(trading_filter)
        
        # Kiwoom logger setup
        self.kiwoom_log_widget.setFormatter(kiwoom_formatter)
        kiwoom_filter = ModuleFilter(['kiwoom'])
        self.kiwoom_log_widget.addFilter(kiwoom_filter)
        
        # Add handlers to root logger
        logging.getLogger().addHandler(self.trading_log_widget)
        logging.getLogger().addHandler(self.kiwoom_log_widget)
        
        # Window settings
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        
        # Set dark theme for the entire window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QStatusBar {
                color: white;
                background-color: #2c3e50;
            }
            QWidget {
                background-color: #1e1e1e;
            }
        """)

    @pyqtSlot(str)
    def update_status(self, message):
        self.status_bar.showMessage(message)

    @pyqtSlot(int, int)
    def update_progress(self, completed, total):
        """Update the progress bar with current trading progress"""
        if total > 0:
            percentage = (completed * 100) // total
            self.progress_bar.setValue(percentage)
            self.progress_label.setText(f"Trading Progress: {completed}/{total}")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("Trading Progress: 0/0") 