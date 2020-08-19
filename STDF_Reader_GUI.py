# -*- coding:utf-8 -*-
###################################################
# STDF Reader Tool                                #
# Version: Beta 0.5                               #
#                                                 #
# Sep. 18, 2019                                   #
# A light STDF reader and analysis tool           #
# A project forked from Thomas Kaunzinger         #
#                                                 #
# References:                                     #
# PySTDF Library                                  #
# PyQt5                                           #
# numpy                                           #
# matplotlib                                      #
# countrymarmot (cp + cpk)                        #
# PyPDF2                                          #
# ZetCode + sentdex (PyQt tutorials)              #
# My crying soul because there's no documentation #
###################################################

###################################################

#######################
# IMPORTING LIBRARIES #
#######################

# import fix_qt_import_error
# from PyQt5.QtWidgets import QWidget, QDesktopWidget, QApplication, QToolTip, QPushButton
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from pystdf.Writers import *

from abc import ABC
import numpy as np
import pandas as pd
import time
import xlsxwriter
import logging
import re
import qtawesome as qta

import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# from numba import jit
from src.Backend import Backend
from src.FileRead import FileReaders
from src.Threads import PdfWriterThread, CsvParseThread, XlsxParseThread, DiagParseThread

Version = 'Beta 0.6.4'


###################################################

########################
# QT GUI FUNCTIONALITY #
########################

# These are the functions for the QMainWindow/widget application objects that run the whole interface
class Application(QMainWindow):  # QWidget):

    # Construct me
    def __init__(self):
        super().__init__()

        # Have to read the imported .txt file but I'm not totally sure how
        self.data = None
        self.number_of_sites = None
        self.list_of_test_numbers = []
        self.list_of_test_numbers_string = []
        self.tnumber_list = []
        self.tname_list = []

        self.test_info_list = []
        self.df_csv = pd.DataFrame()
        self.sdr_parse = []
        self.list_of_duplicate_test_numbers = []
        self.s2s_correlation_report_df = pd.DataFrame()

        # exitAct = QAction(QIcon('exit.png'), '&Exit', self)
        # exitAct.setShortcut('Ctrl+Q')
        # exitAct.triggered.connect(qApp.quit)
        # aboutAct = QAction(QIcon('about.png'), '&About', self)
        # aboutAct.triggered.connect(self.aboutecho)
        #
        # menubar = self.menuBar()
        # fileMenu = menubar.addMenu('&File')
        # helpMenu = menubar.addMenu('&Help')
        # fileMenu.addAction(exitAct)
        # helpMenu.addAction(aboutAct)

        # Set icon for window, the img path should be full absolute path for compiling
        self.pix = QPixmap(pathname + r'\img\icon.ico')
        icon = QIcon()
        icon.addPixmap(self.pix, QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)

        # Set the window title
        self.window_title = QLabel()
        self.window_title.setText('STDF Reader For AP ' + Version)
        self.window_title.setFont(QFont("Times", 14, weight=QFont.Bold))
        self.window_title_img = QLabel()
        self.window_title_img.setPixmap(self.pix)
        # self.window_title_img.setGeometry(0, 100, 3, 3)
        self.window_title_img.setScaledContents(True)
        self.window_title_img.setMaximumHeight(20)
        self.window_title_img.setMaximumWidth(20)
        # lb1 = QLabel(self)
        # lb1.setGeometry(0, 250, 300, 200)
        # lb1.setPixmap(pix)
        # lb1.setStyleSheet("border: 2px solid red")
        # lb1.setScaledContents(True)

        self.button_close = QPushButton(qta.icon('mdi.window-close'), '')
        self.button_about = QPushButton(qta.icon('mdi.window-maximize'), '')
        self.button_mini = QPushButton(qta.icon('mdi.window-minimize'), '')
        self.button_close.clicked.connect(self.close)
        self.button_about.clicked.connect(self.aboutecho)
        self.button_mini.clicked.connect(self.showMinimized)

        self.status_text = QLabel()
        self.status_text.setText('Welcome!')
        self.status_text.setFont(QFont("Times", 12, weight=QFont.Bold))

        self.step_1 = QGroupBox('Step 1: Convert to CSV')

        self.step_2 = QGroupBox('Step 2: Upload CSV for Analysis')
        # self.step_2.setTitle('Step 2: Upload CSV for Analysis')

        # Button to parse to .txt
        self.stdf_upload_button_xlsx = QPushButton(qta.icon('fa5s.file-excel', color='green', color_active='black'),
                                                   'Parse STD/STDF to .xlsx table')
        self.stdf_upload_button_xlsx.setToolTip(
            'Browse for a file ending in .std to create a parsed .xlsx file')
        self.stdf_upload_button_xlsx.clicked.connect(self.open_parsing_dialog_xlsx)

        # Button to parse to .csv
        self.stdf_upload_button = QPushButton(qta.icon('fa5s.file-csv', color='green', color_active='black'),
                                              'Parse STD/STDF to .csv log')
        self.stdf_upload_button.setToolTip(
            'Browse for stdf to create .csv file. This is helpful when doing data analysis')
        self.stdf_upload_button.clicked.connect(self.open_parsing_dialog_csv)

        # Button to upload the .txt file to work with
        self.txt_upload_button = QPushButton(qta.icon('fa5s.file-upload', color='blue', color_active='black'),
                                             'Upload parsed .csv file')
        self.txt_upload_button.setToolTip(
            'Browse for the .csv file containing the parsed STDF data')
        self.txt_upload_button.clicked.connect(self.open_text)

        # Generates a summary of the loaded text
        self.generate_summary_button = QPushButton(qta.icon('mdi.google-analytics', color='blue', color_active='black'),
                                                   'Generate data analysis report')
        self.generate_summary_button.setToolTip(
            'Generate a .xlsx data analysis report for the uploaded parsed .csv')
        self.generate_summary_button.clicked.connect(self.generate_analysis_report)

        # Selects a test result for the desired
        self.select_test_menu = ComboCheckBox()  # ComboCheckBox() # QComboBox()
        self.select_test_menu.setToolTip(
            'Select the tests to produce the PDF results for')

        # Button to generate the test results for the desired tests from the selected menu
        self.generate_pdf_button = QPushButton(qta.icon('fa5s.file-pdf', color='red', color_active='black'),
                                               'Generate .pdf from selected tests')
        self.generate_pdf_button.setToolTip(
            'Generate a .pdf file with the selected tests from the parsed .txt')
        self.generate_pdf_button.clicked.connect(self.plot_list_of_tests)

        self.limit_toggle = QCheckBox('Plot against failure limits', self)
        self.limit_toggle.setChecked(True)
        self.limit_toggle.stateChanged.connect(self.toggler)
        self.limits_toggled = True

        self.group_toggle = QCheckBox('Plot tendency by file', self)
        self.group_toggle.setChecked(False)
        self.group_toggle.stateChanged.connect(self.group_by_file)
        self.group_toggled = False

        self.plot_tests_button = QPushButton(qta.icon('mdi.trending-up', color='red', color_active='orange'),
                                               'Plot Selected Tests')
        self.plot_tests_button.setToolTip('Plot Selected Tests\' Trendency')
        self.plot_tests_button.clicked.connect(self.plot_list_of_tests_on_one_figure)

        # Generates a correlation report for all sites of the loaded data
        self.generate_correlation_button = QPushButton(
            qta.icon('mdi.file-compare', color='black', color_active='black'),
            'Generate correlation report of multiple stdf files')
        self.generate_correlation_button.setToolTip(
            'Generate a .xlsx correlation report of 2 stdf files for the uploaded parsed .csv')
        self.generate_correlation_button.clicked.connect(self.generate_correlation_report)

        # Generates a correlation report for site2site compare
        self.generate_correlation_button_s2s = QPushButton(
            qta.icon('mdi.sitemap', color='yellow', color_active='black'),
            'Generate correlation of Site2Site')
        self.generate_correlation_button_s2s.setToolTip(
            'Generate an Site2Site correlation report')
        self.generate_correlation_button_s2s.clicked.connect(self.generate_s2s_correlation_report)

        # Selects a test result for s2s correlation
        self.select_s2s_test_menu = ComboCheckBox()  # ComboCheckBox() # QComboBox()
        self.select_s2s_test_menu.setToolTip(
            'Select the tests to produce the heatmap results for site-to-site correlation')

        # Button to generate the s2s test results for the desired tests from the selected s2s menu
        self.generate_heatmap_button = QPushButton(
            qta.icon('mdi.chart-scatter-plot', color='orange', color_active='black'),
            'Generate heatmap from selected Site2Site tests')
        self.generate_heatmap_button.setToolTip(
            'Generate a heatmap with the selected s2s tests from the parsed .csv')
        self.generate_heatmap_button.clicked.connect(
            lambda: self.make_s2s_correlation_heatmap(self.s2s_correlation_report_df))

        # Selects tests for extracting sub-CSV
        self.select_test_for_subcsv_menu = ComboCheckBox()
        self.select_test_for_subcsv_menu.setToolTip('Select the tests to produce the sub-CSV for analysis')

        # Extract a sub-CSV log
        self.extract_subcsv = QPushButton(qta.icon('fa5s.file-csv', color='green', color_active='black'),
                                          'Extract a sub-CSV log for chosen tests')
        self.extract_subcsv.setToolTip('Extract a sub-CSV log for chosen tests')
        self.extract_subcsv.clicked.connect(self.make_subcsv_for_chosen_tests)

        # Convert STR/PSR to ASCII log
        self.convert_SDTFV42007_to_ASCII = QPushButton(qta.icon('fa5s.file-csv', color='green', color_active='black'),
                                          'Convert Diagnosis STDFV4-2007.1 to ASCII log')
        self.convert_SDTFV42007_to_ASCII.setToolTip('Convert STR/PSR to Mentor like ASCII log')
        self.convert_SDTFV42007_to_ASCII.clicked.connect(self.open_parsing_diagnosis_ascii)

        self.progress_bar = QProgressBar()

        self.WINDOW_SIZE = (700, 300)
        self.file_path = None
        self.text_file_location = self.file_path

        self.setFixedSize(self.WINDOW_SIZE[0], self.WINDOW_SIZE[1])
        self.center()
        self.setWindowTitle('STDF Reader For AP ' + Version)

        self.selected_tests = []

        self.file_selected = False

        self.threaded_task = PdfWriterThread(file_path=self.file_path, all_data=self.df_csv,
                                             ptr_data=self.test_info_list, number_of_sites=self.number_of_sites,
                                             selected_tests=self.selected_tests, limits_toggled=self.limits_toggled,
                                             list_of_test_numbers=self.list_of_test_numbers, site_list=self.sdr_parse,
                                             group_by_file=self.group_toggled)

        self.threaded_task.notify_progress_bar.connect(self.on_progress)
        self.threaded_task.notify_status_text.connect(self.on_update_text)

        self.threaded_csv_parser = CsvParseThread(file_path=self.file_path)
        self.threaded_csv_parser.notify_status_text.connect(
            self.on_update_text)

        self.threaded_xlsx_parser = XlsxParseThread(file_path=self.file_path)
        self.threaded_xlsx_parser.notify_status_text.connect(self.on_update_text)

        self.threaded_diagnosis_parser = DiagParseThread(file_path=self.file_path)
        self.threaded_diagnosis_parser.notify_status_text.connect(self.on_update_text)

        self.generate_pdf_button.setEnabled(False)
        self.select_test_menu.setEnabled(False)
        self.generate_summary_button.setEnabled(False)
        self.limit_toggle.setEnabled(False)
        self.group_toggle.setEnabled(False)
        self.plot_tests_button.setEnabled(False)

        self.generate_correlation_button.setEnabled(False)
        self.generate_correlation_button_s2s.setEnabled(False)
        self.select_s2s_test_menu.setEnabled(False)
        self.generate_heatmap_button.setEnabled(False)

        self.select_test_for_subcsv_menu.setEnabled(False)
        self.extract_subcsv.setEnabled(False)

        self.main_window()

    # Tab for data analysis
    def tab_data_analysis(self):
        layout = QGridLayout()
        layout.addWidget(self.generate_summary_button, 0, 0, 1, 4)
        layout.addWidget(self.select_test_menu, 1, 0, 1, 4)
        layout.addWidget(self.generate_pdf_button, 2, 0)
        layout.addWidget(self.limit_toggle, 2, 1)
        layout.addWidget(self.group_toggle, 2, 2)
        layout.addWidget(self.plot_tests_button, 2, 3)
        self.data_analysis_tab.setLayout(layout)

    # Tab for data correlation
    def tab_data_correlation(self):
        layout = QGridLayout()
        layout.addWidget(self.generate_correlation_button, 0, 0)
        layout.addWidget(self.generate_correlation_button_s2s, 0, 1)
        layout.addWidget(self.select_s2s_test_menu, 1, 0, 1, 2)
        layout.addWidget(self.generate_heatmap_button, 2, 0)
        self.correlation_tab.setLayout(layout)

    # Tab for tools
    def tab_tools(self):
        layout = QGridLayout()
        layout.addWidget(self.stdf_upload_button_xlsx, 0, 0)
        layout.addWidget(self.convert_SDTFV42007_to_ASCII, 0, 1)
        layout.addWidget(self.select_test_for_subcsv_menu, 1, 0, 1, 2)
        layout.addWidget(self.extract_subcsv, 2, 0)
        self.tools_tab.setLayout(layout)

    # Main interface method
    def main_window(self):
        # self.setGeometry(300, 300, 300, 200)
        # self.resize(900, 700)
        self.setWindowTitle('STDF Reader For AP ' + Version)

        # Layout
        layout = QGridLayout()
        self.setLayout(layout)

        # Adds the widgets together in the grid
        # self.window_title.setAlignment(Qt.AlignCenter)
        # self.window_title_img.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.window_title_img, 0, 11, 1, 1)
        layout.addWidget(self.window_title, 0, 12, 1, 10)
        layout.addWidget(self.button_mini, 0, 29, 1, 1)
        layout.addWidget(self.button_about, 0, 30, 1, 1)
        layout.addWidget(self.button_close, 0, 31, 1, 1)
        layout.addWidget(self.status_text, 1, 0, 1, 32)
        # layout.addWidget(self.stdf_upload_button_xlsx, 2, 0, 1, 16)
        # layout.addWidget(self.test_frame, 2, 0, 2, 16)

        vbox = QVBoxLayout()
        vbox.addWidget(self.stdf_upload_button)
        self.step_1.setLayout(vbox)
        layout.addWidget(self.step_1, 2, 0, 2, 16)
        # layout.addWidget(self.stdf_upload_button, 3, 3, 1, 12)
        vbox2 = QVBoxLayout()
        vbox2.addWidget(self.txt_upload_button)
        self.step_2.setLayout(vbox2)
        layout.addWidget(self.step_2, 2, 16, 2, 16)
        # layout.addWidget(self.txt_upload_button, 3, 18, 1, 12)

        tabs = QTabWidget(self)
        self.data_analysis_tab = QWidget()
        self.correlation_tab = QWidget()
        self.tools_tab = QWidget()
        self.tab_data_analysis()
        self.tab_data_correlation()
        self.tab_tools()
        tabs.addTab(self.data_analysis_tab, 'Data Analysis')
        tabs.addTab(self.correlation_tab, 'Data Correlation')
        tabs.addTab(self.tools_tab, 'Some Tools')
        layout.addWidget(tabs, 5, 0, 4, 32)
        layout.addWidget(self.progress_bar, 10, 0, 1, 32)

        # Create an QWidget, and use layout_grid
        widget = QWidget()
        widget.setLayout(layout)
        # Set 'widget' as central widget
        self.setCentralWidget(widget)

        self.button_close.setStyleSheet(
            '''QPushButton{background:#F76677;border-radius:5px;}QPushButton:hover{background:red;}''')
        self.button_about.setStyleSheet(
            '''QPushButton{background:#F7D674;border-radius:5px;}QPushButton:hover{background:yellow;}''')
        self.button_mini.setStyleSheet(
            '''QPushButton{background:#6DDF6D;border-radius:5px;}QPushButton:hover{background:green;}''')

        self.setWindowOpacity(0.95)  # 设置窗口透明度
        self.setWindowFlag(Qt.FramelessWindowHint)  # 隐藏边框
        pe = QPalette()
        self.setAutoFillBackground(True)
        # pe.setColor(QPalette.Window, Qt.lightGray)  # 设置背景色
        pe.setColor(QPalette.Background, Qt.lightGray)
        self.setPalette(pe)

        # Window settings
        self.show()

    def aboutecho(self):
        QMessageBox.information(
            self, 'About', 'Author：Chao Zhou \n verion ' + Version + ' \n 感谢您的使用！ \n zhouchao486@gmail.com ',
            QMessageBox.Ok)

    # Centers the window
    def center(self):
        window = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        window.moveCenter(center_point)
        self.move(window.topLeft())

    # 重写三个方法使我们的Example窗口支持拖动,上面参数window就是拖动对象
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))

    def mouseMoveEvent(self, QMouseEvent):
        if Qt.LeftButton and self.m_drag:
            self.move(QMouseEvent.globalPos() - self.m_DragPosition)
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_drag = False
        self.setCursor(QCursor(Qt.ArrowCursor))

    # Opens and reads a file to parse the data
    def open_parsing_dialog(self):
        self.status_text.setText('Parsing to .txt, please wait...')
        filterboi = 'STDF (*.stdf *.std)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open STDF File', filter=filterboi)

        if filepath[0] == '':

            self.status_text.setText('Please select a file')
            pass

        else:

            self.status_text.update()
            FileReaders.process_file(filepath[0])
            self.status_text.setText(
                str(filepath[0].split('/')[-1] + '_parsed.txt created!'))

    # Opens and reads a file to parse the data to an csv
    def open_parsing_dialog_csv(self):
        # I can not figure out the process when parsing STDF, so...
        self.progress_bar.setMinimum(0)

        # Move QFileDialog out of QThread, in case of error under win 7
        self.status_text.setText('Parsing to .csv file, please wait...')
        filterboi = 'STDF (*.stdf *.std);;GZ (*.stdf.gz *.std.gz)'
        filepath = QFileDialog.getOpenFileNames(
            caption='Open STDF or GZ File', filter=filterboi)

        self.status_text.update()
        self.stdf_upload_button.setEnabled(False)
        # self.progress_bar.setMaximum(0)
        self.threaded_csv_parser = CsvParseThread(filepath)
        self.threaded_csv_parser.notify_progress_bar.connect(self.on_progress)
        self.threaded_csv_parser.notify_status_text.connect(self.on_update_text)
        self.threaded_csv_parser.finished.connect(self.set_progress_bar_max)
        self.threaded_csv_parser.start()
        self.stdf_upload_button.setEnabled(True)
        # self.main_window()

    # Opens and reads a file to parse the data to an xlsx
    def open_parsing_dialog_xlsx(self):

        self.progress_bar.setMinimum(0)

        self.status_text.setText('Parsing to .xlsx file, please wait...')
        filterboi = 'STDF (*.stdf *.std)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open STDF File', filter=filterboi)

        self.status_text.update()
        self.stdf_upload_button_xlsx.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.threaded_xlsx_parser = XlsxParseThread(filepath[0])
        self.threaded_xlsx_parser.notify_status_text.connect(self.on_update_text)
        self.threaded_xlsx_parser.finished.connect(self.set_progress_bar_max)
        self.threaded_xlsx_parser.start()
        self.stdf_upload_button_xlsx.setEnabled(True)
        # self.main_window()

    # Convert STDF V4 2007.1 to Mentor like log
    def open_parsing_diagnosis_ascii(self):
        self.progress_bar.setMinimum(0)
        self.status_text.setText('Parsing Diagnosis file to .csv, please wait...')
        filterboi = 'STDF (*.stdf *.std);;GZ (*.stdf.gz *.std.gz)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open STDF or GZ File', filter=filterboi)
        self.status_text.update()
        self.convert_SDTFV42007_to_ASCII.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.threaded_diagnosis_parser = DiagParseThread(filepath[0])
        self.threaded_diagnosis_parser.notify_status_text.connect(self.on_update_text)
        self.threaded_diagnosis_parser.finished.connect(self.set_progress_bar_max)
        self.threaded_diagnosis_parser.start()
        self.convert_SDTFV42007_to_ASCII.setEnabled(True)
        # self.main_window()

    def set_progress_bar_max(self):
        self.progress_bar.setMaximum(100)
        QMessageBox.information(self, 'Go ahead, bro', 'Parse Complete !', QMessageBox.Ok)

    # Checks if the toggle by limits mark is checked or not
    def toggler(self, state):

        if state == Qt.Checked:
            self.limits_toggled = True
        else:
            self.limits_toggled = False

    # Checks if the plot rhe tendency group by file or not
    def group_by_file(self, state):

        if state == Qt.Checked:
            self.group_toggled = True
        else:
            self.group_toggled = False

    # Opens and reads a file to parse the data. Much of this is what was done in main() from the text version
    def open_text(self):
        # Only accepts text files
        filterboi = 'CSV Table (*.csv)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open .csv File', filter=filterboi)

        self.file_path = filepath[0]

        # Because you can open it and select nothing smh
        if self.file_path != '':

            self.txt_upload_button.setEnabled(False)

            self.progress_bar.setValue(0)
            self.list_of_test_numbers = []
            self.list_of_duplicate_test_numbers = []
            startt = time.time()

            if self.file_path.endswith(".txt"):
                pass
            elif self.file_path.endswith(".std"):
                pass
            elif self.file_path.endswith(".csv"):
                self.df_csv = pd.read_csv(self.file_path, header=[0, 1, 2, 3, 4])  # , dtype=str)
                # self.df_csv.replace(r'\(F\)','',regex=True, inplace=True)
                # self.df_csv.iloc[:,12:] = self.df_csv.iloc[:,12:].astype('float')

                # Extracts the test name for the selecting
                tmp_pd = self.df_csv.columns
                self.single_columns = tmp_pd.get_level_values(4).values.tolist()[:16]  # Get the part info
                self.tnumber_list = tmp_pd.get_level_values(4).values.tolist()[16:]
                self.tname_list = tmp_pd.get_level_values(0).values.tolist()[16:]
                self.test_info_list = tmp_pd.values.tolist()[16:]
                self.list_of_test_numbers_string = [j + ' - ' + i for i, j in
                                                    zip(self.tname_list, self.tnumber_list)]
                # Change the multi-level columns to single level columns
                self.single_columns = self.single_columns + self.list_of_test_numbers_string
                self.df_csv.columns = self.single_columns

                # Data cleaning, get rid of '(F)'
                self.df_csv.replace(r'\(F\)', '', regex=True, inplace=True)
                self.df_csv.iloc[:, 16:] = self.df_csv.iloc[:, 16:].astype('float')
                self.df_csv['X_COORD'] = self.df_csv['X_COORD'].astype(int)
                self.df_csv['Y_COORD'] = self.df_csv['Y_COORD'].astype(int)
                self.df_csv['SOFT_BIN'] = self.df_csv['SOFT_BIN'].astype(int)
                self.df_csv['HARD_BIN'] = self.df_csv['HARD_BIN'].astype(int)

                # Extract the test name and test number list
                self.list_of_test_numbers = [list(z) for z in (zip(self.tnumber_list, self.tname_list))]

                # Get site array
                self.sdr_parse = self.df_csv['SITE_NUM'].unique()
                self.number_of_sites = len(self.sdr_parse)

            endt = time.time()
            print('读取时间：', endt - startt)
            logging.info('Debug message: ' + '读取时间：' + str(endt - startt))
            # sdr_parse = self.sdr_data[0].split("|")

            self.progress_bar.setValue(35)

            self.file_selected = True

            self.select_test_menu.loadItems(self.list_of_test_numbers_string)
            self.select_s2s_test_menu.loadItems(self.list_of_test_numbers_string)
            self.select_test_for_subcsv_menu.loadItems(self.list_of_test_numbers_string)

            self.selected_tests = []

            # log parsed document, if duplicate test number exist, show warning !
            if len(self.list_of_duplicate_test_numbers) > 0:
                self.status_text.setText(
                    'Parsed .csv uploaded! But Duplicate Test Number Found! Please Check \'duplicate_test_number.csv\'')
            else:
                self.status_text.setText('Parsed .csv uploaded!')

            self.progress_bar.setValue(100)
            self.txt_upload_button.setEnabled(True)
            self.generate_pdf_button.setEnabled(True)
            self.select_test_menu.setEnabled(True)
            self.generate_summary_button.setEnabled(True)
            self.limit_toggle.setEnabled(True)
            self.group_toggle.setEnabled(True)
            self.plot_tests_button.setEnabled(True)

            self.generate_correlation_button.setEnabled(True)
            self.generate_correlation_button_s2s.setEnabled(True)
            self.select_s2s_test_menu.setEnabled(False)
            self.generate_heatmap_button.setEnabled(False)

            self.select_test_for_subcsv_menu.setEnabled(True)
            self.extract_subcsv.setEnabled(True)
            self.main_window()

        else:

            self.status_text.setText('Please select a file')

    # find out the duplicate test number with differnet test name
    def list_duplicates_of(self, seq, item, start_index):  # start_index is to reduce the complex
        start_at = -1
        locs = []
        while True:
            try:
                loc = seq.index(item, start_at + 1)
            except ValueError:
                break
            else:
                locs.append(start_index + loc)
                start_at = loc
                # Just find the first duplicate to reduce complex
                if len(locs) == 2:
                    break
        return locs

    # Create a xlsx report including Data Statistics, Duplicate Test Number and Wafer Map
    def generate_analysis_report(self):
        analysis_report_name = str(self.file_path[:-11] + "_analysis_report.xlsx")
        self.status_text.setText(
            str(analysis_report_name + " is generating..."))

        startt = time.time()
        data_summary = self.make_data_summary_report()
        endt = time.time()
        print('data summary Time: ', endt - startt)
        logging.info('Debug message: ' + 'data summary Time: ' + str(endt - startt))

        startt = time.time()
        duplicate_number_report = self.make_duplicate_num_report()
        self.progress_bar.setValue(82)
        endt = time.time()
        print('duplicate number Time: ', endt - startt)
        logging.info('Debug message: ' + 'duplicate number Time: ' + str(endt - startt))

        startt = time.time()
        bin_summary_list = self.make_bin_summary()
        self.progress_bar.setValue(85)
        endt = time.time()
        print('bin summary Time: ', endt - startt)
        logging.info('Debug message: ' + 'bin summary Time: ' + str(endt - startt))

        startt = time.time()
        wafer_map_list = self.make_wafer_map()
        self.progress_bar.setValue(88)
        endt = time.time()
        print('wafer map Time: ', endt - startt)
        logging.info('Debug message: ' + 'wafer map Time: ' + str(endt - startt))

        startt = time.time()

        # In case someone has the file open
        try:
            with pd.ExcelWriter(analysis_report_name, engine='xlsxwriter') as writer:
                workbook = writer.book
                # Light red fill for Bin 2XXX
                format_2XXX = workbook.add_format({'bg_color': '#FF0000'})
                # Orange fill for Bin 3XXX
                format_3XXX = workbook.add_format({'bg_color': '#FF6600'})
                # Dark red fill for Bin 4XXX
                format_4XXX = workbook.add_format({'bg_color': '#FFC7CE'})
                # Light yellow for Bin 6XXX
                format_6XXX = workbook.add_format({'bg_color': '#FFEB9C'})
                # Dark yellow for Bin 9XXX
                format_9XXX = workbook.add_format({'bg_color': '#9C6500'})
                # Green for Bin 1/1XXX
                format_1XXX = workbook.add_format({'bg_color': '#008000'})
                # Dark green for Bin 7XXX
                format_7XXX = workbook.add_format({'bg_color': '#C6EFCE'})
                # Add width and format for first column
                format1 = workbook.add_format({'align': 'left'})

                data_summary.to_excel(writer, sheet_name='Data Statistics')
                row_table, column_table = data_summary.shape
                worksheet = writer.sheets['Data Statistics']
                # Freeze pane on the top row
                worksheet.freeze_panes(1, 0)
                # Set the width and align
                worksheet.set_column('A:A', 25, format1)

                worksheet.conditional_format(1, 12, row_table, 12,
                                             {'type': 'cell', 'criteria': '<',
                                              'value': 3.3, 'format': format_4XXX})
                worksheet.conditional_format(1, 13, row_table, 13,
                                             {'type': 'cell', 'criteria': '<',
                                              'value': 1.33, 'format': format_4XXX})
                worksheet.conditional_format(1, 14, row_table, 14,
                                             {'type': 'cell', 'criteria': '<',
                                              'value': 1.33, 'format': format_4XXX})
                worksheet.conditional_format(1, 15, row_table, 15,
                                             {'type': 'cell', 'criteria': '<',
                                              'value': 1.33, 'format': format_4XXX})
                worksheet.autofilter(0, 0, row_table, column_table)
                self.progress_bar.setValue(89)
                duplicate_number_report.to_excel(writer, sheet_name='Duplicate Test Number')
                self.progress_bar.setValue(90)

                # Output Bin Summary Sheet
                start_row = 0
                for i in range(len(bin_summary_list)):
                    bin_summary = bin_summary_list[i]
                    row_table, column_table = bin_summary.shape
                    bin_summary.to_excel(writer, sheet_name='Bin Summary', startrow=start_row)

                    worksheet = writer.sheets['Bin Summary']
                    worksheet.conditional_format(start_row + 1, 0,
                                                 start_row + row_table, 0,
                                                 {'type': 'cell',
                                                  'criteria': 'between',
                                                  'minimum': 1,
                                                  'maximum': 1999,
                                                  'format': format_1XXX})
                    worksheet.conditional_format(start_row + 1, 0,
                                                 start_row + row_table, 0,
                                                 {'type': 'cell',
                                                  'criteria': 'between',
                                                  'minimum': 2000,
                                                  'maximum': 2999,
                                                  'format': format_2XXX})
                    worksheet.conditional_format(start_row + 1, 0,
                                                 start_row + row_table, 0,
                                                 {'type': 'cell',
                                                  'criteria': 'between',
                                                  'minimum': 3000,
                                                  'maximum': 3999,
                                                  'format': format_3XXX})
                    worksheet.conditional_format(start_row + 1, 0,
                                                 start_row + row_table, 0,
                                                 {'type': 'cell',
                                                  'criteria': 'between',
                                                  'minimum': 4000,
                                                  'maximum': 4999,
                                                  'format': format_4XXX})
                    worksheet.conditional_format(start_row + 1, 0,
                                                 start_row + row_table, 0,
                                                 {'type': 'cell',
                                                  'criteria': 'between',
                                                  'minimum': 6000,
                                                  'maximum': 6999,
                                                  'format': format_6XXX})
                    worksheet.conditional_format(start_row + 1, 0,
                                                 start_row + row_table, 0,
                                                 {'type': 'cell',
                                                  'criteria': 'between',
                                                  'minimum': 7000,
                                                  'maximum': 7999,
                                                  'format': format_7XXX})
                    worksheet.conditional_format(start_row + 1, 0,
                                                 start_row + row_table, 0,
                                                 {'type': 'cell',
                                                  'criteria': 'between',
                                                  'minimum': 9000,
                                                  'maximum': 9999,
                                                  'format': format_9XXX})
                    self.progress_bar.setValue(90 + int(i / len(bin_summary_list) * 5))
                    start_row = start_row + row_table + 3

                # Output Wafer Map Sheet: total wafer map and maps for each site
                start_row = 0
                for i in range(len(wafer_map_list)):
                    start_column = 0
                    for j in range(len(wafer_map_list[i])):
                        wafer_map = wafer_map_list[i][j]
                        row_table, column_table = wafer_map.shape
                        wafer_map.to_excel(writer, sheet_name='Wafer Map', startrow=start_row, startcol=start_column)

                        worksheet = writer.sheets['Wafer Map']
                        worksheet.conditional_format(start_row + 1, start_column + 1,
                                                     start_row + row_table, start_column + column_table,
                                                     {'type': 'cell',
                                                      'criteria': 'between',
                                                      'minimum': 1,
                                                      'maximum': 1999,
                                                      'format': format_1XXX})
                        worksheet.conditional_format(start_row + 1, start_column + 1,
                                                     start_row + row_table, start_column + column_table,
                                                     {'type': 'cell',
                                                      'criteria': 'between',
                                                      'minimum': 2000,
                                                      'maximum': 2999,
                                                      'format': format_2XXX})
                        worksheet.conditional_format(start_row + 1, start_column + 1,
                                                     start_row + row_table, start_column + column_table,
                                                     {'type': 'cell',
                                                      'criteria': 'between',
                                                      'minimum': 3000,
                                                      'maximum': 3999,
                                                      'format': format_3XXX})
                        worksheet.conditional_format(start_row + 1, start_column + 1,
                                                     start_row + row_table, start_column + column_table,
                                                     {'type': 'cell',
                                                      'criteria': 'between',
                                                      'minimum': 4000,
                                                      'maximum': 4999,
                                                      'format': format_4XXX})
                        worksheet.conditional_format(start_row + 1, start_column + 1,
                                                     start_row + row_table, start_column + column_table,
                                                     {'type': 'cell',
                                                      'criteria': 'between',
                                                      'minimum': 6000,
                                                      'maximum': 6999,
                                                      'format': format_6XXX})
                        worksheet.conditional_format(start_row + 1, start_column + 1,
                                                     start_row + row_table, start_column + column_table,
                                                     {'type': 'cell',
                                                      'criteria': 'between',
                                                      'minimum': 7000,
                                                      'maximum': 7999,
                                                      'format': format_7XXX})
                        worksheet.conditional_format(start_row + 1, start_column + 1,
                                                     start_row + row_table, start_column + column_table,
                                                     {'type': 'cell',
                                                      'criteria': 'between',
                                                      'minimum': 9000,
                                                      'maximum': 9999,
                                                      'format': format_9XXX})

                        start_column = start_column + column_table + 3
                        self.progress_bar.setValue(95 + int(i / len(bin_summary_list) * 5))
                    start_row = start_row + row_table + 3
                self.progress_bar.setValue(100)
                endt = time.time()
                print('XLSX 生成时间: ', endt - startt)
                logging.info('Debug message: ' + 'XLSX 生成时间: ' + str(endt - startt))
                self.status_text.setText(
                    str(analysis_report_name.split('/')[-1] + " written successfully!"))
        except xlsxwriter.exceptions.FileCreateError:  # PermissionError:
            self.status_text.setText(
                str("Please close " + analysis_report_name.split('/')[-1]))
            self.progress_bar.setValue(0)

    # Handler for the summary button to generate a csv table results file for all data
    def make_data_summary_report(self):

        # Won't perform action unless there's actually a file
        if self.file_selected:
            self.progress_bar.setValue(0)
            print_data_flag = False
            if '_LOOP' in self.file_path.upper():
                print_data_flag = True
            table = self.get_summary_table(self.df_csv, self.test_info_list, self.number_of_sites,
                                           self.list_of_test_numbers, True, True, print_data_flag)
            self.progress_bar.setValue(80)
        else:
            self.status_text.setText('Please select a file')
        return table

    def make_duplicate_num_report(self):
        # Check the duplicate test number
        test_number_list = self.tnumber_list
        test_name_list = self.tname_list
        if len(test_number_list) != len(set(test_number_list)):
            for i in range(len(test_number_list)):
                dup_list = self.list_duplicates_of(test_number_list[i:], test_number_list[i], i)
                if len(dup_list) > 1:
                    self.list_of_duplicate_test_numbers.append(
                        [test_number_list[dup_list[0]], test_name_list[i], test_name_list[dup_list[1]]])
        # Log duplicate test number item from list, if exist
        log_csv = pd.DataFrame({'name': ['不错哟 !!!']})
        if len(self.list_of_duplicate_test_numbers) > 0:
            log_csv = pd.DataFrame(self.list_of_duplicate_test_numbers,
                                   columns=['Test Number', 'Test Name', 'Test Name'])
        return log_csv

    def make_bin_summary(self):
        all_bin_summary_list = []
        lot_id_list = self.df_csv['LOT_ID'].unique()
        for lot_id in lot_id_list:
            single_lot_df = self.df_csv[self.df_csv['LOT_ID'].isin([lot_id])]
            wafer_id_list = single_lot_df['WAFER_ID'].unique()
            for wafer_id in wafer_id_list:
                single_wafer_df = single_lot_df[single_lot_df['WAFER_ID'].isin([wafer_id])]
                die_id = str(single_wafer_df['LOT_ID'].iloc[0]) + ' - ' + str(single_wafer_df['WAFER_ID'].iloc[0])
                retest_die_df = single_wafer_df[single_wafer_df['RC'].isin(['Retest'])]
                retest_die_np = retest_die_df[['X_COORD', 'Y_COORD']].values
                mask = (single_wafer_df.X_COORD.values == retest_die_np[:, None, 0]) & \
                       (single_wafer_df.Y_COORD.values == retest_die_np[:, None, 1]) & \
                       (single_wafer_df['RC'].isin(['First']).to_numpy())
                single_wafer_df = single_wafer_df[~mask.any(axis=0)]
                bin_summary_pd = single_wafer_df.pivot_table('PART_ID', index=['SOFT_BIN', 'BIN_DESC'],
                                                             columns='SITE_NUM',
                                                             aggfunc='count', margins=True, fill_value=0).copy()
                # bin_summary_pd = sbin_counts.rename(index=self.sbin_description).copy()
                bin_summary_pd.index.rename([die_id, 'BIN_DESC'], inplace=True)
                all_bin_summary_list.append(bin_summary_pd)
        # self.bin_summary_pd.to_csv(self.filename + '_bin_summary.csv')
        # f = open(self.file_path[:-11] + '_bin_summary.csv', 'w')
        # for temp_df in all_bin_summary_list:
        #     temp_df.to_csv(f, line_terminator='\n')
        #     f.write('\n')
        # f.close()
        return all_bin_summary_list

    def make_wafer_map(self):
        # Get wafer map
        all_wafer_map_list = []
        lot_id_list = self.df_csv['LOT_ID'].unique()
        for lot_id in lot_id_list:
            single_lot_df = self.df_csv[self.df_csv['LOT_ID'].isin([lot_id])]
            wafer_id_list = single_lot_df['WAFER_ID'].unique()
            for wafer_id in wafer_id_list:
                tmp_wafer_map_list = []
                single_wafer_df = single_lot_df[single_lot_df['WAFER_ID'].isin([wafer_id])]
                die_id = str(single_wafer_df['LOT_ID'].iloc[0]) + ' - ' + str(single_wafer_df['WAFER_ID'].iloc[0])
                wafer_map_df = single_wafer_df.pivot_table(values='SOFT_BIN', index='Y_COORD', columns='X_COORD',
                                                           aggfunc=lambda x: int(tuple(x)[-1]))
                wafer_map_df.index.name = die_id
                # Sort Y from low to high
                wafer_map_df.sort_index(axis=0, ascending=False, inplace=True)
                tmp_wafer_map_list.append(wafer_map_df)

                site_num_list = single_wafer_df['SITE_NUM'].unique()
                for site_num in site_num_list:
                    single_site_df = single_wafer_df[single_wafer_df['SITE_NUM'].isin([site_num])]
                    site_id = die_id + ' - Site ' + str(site_num)
                    single_site_wafer_map_df = single_site_df.pivot_table(values='SOFT_BIN',
                                                                          index='Y_COORD',
                                                                          columns='X_COORD',
                                                                          aggfunc=lambda x: int(tuple(x)[-1]))
                    single_site_wafer_map_df.index.name = site_id
                    # Sort Y from low to high
                    single_site_wafer_map_df.sort_index(axis=0, ascending=False, inplace=True)
                    tmp_wafer_map_list.append(single_site_wafer_map_df)
                all_wafer_map_list.append(tmp_wafer_map_list)
        # wafer_map_df.to_csv(self.filename + '_wafer_map.csv')
        # pd.concat(all_wafer_map_list).to_csv(self.filename + '_wafer_map.csv')
        # f = open(self.file_path[:-11] + '_wafer_map.csv', 'w')
        # for temp_df in all_wafer_map_list:
        #     temp_df.to_csv(f, line_terminator='\n')
        #     f.write('\n')
        # f.close()
        return all_wafer_map_list

    def generate_correlation_report(self):
        correlation_report_name = str(self.file_path[:-11] + "_correlation_report.xlsx")
        self.status_text.setText(
            str(correlation_report_name.split('/')[-1] + " is generating..."))

        correlation_table, file_list = self.make_correlation_table()
        wafer_map_cmp_list = self.make_wafer_map_cmp()
        self.progress_bar.setValue(95)

        # In case someone has the file open
        try:
            with pd.ExcelWriter(correlation_report_name, engine='xlsxwriter') as writer:
                workbook = writer.book
                # Light red fill for Bin 4XXX
                format_4XXX = workbook.add_format({'bg_color': '#FFC7CE'})
                # Add width and format for first column
                format1 = workbook.add_format({'align': 'left'})

                # Write correlation table
                correlation_table.to_excel(writer, sheet_name='2 STDF correlation table')
                row_table, column_table = correlation_table.shape
                worksheet = writer.sheets['2 STDF correlation table']

                # Freeze pane on the top row
                worksheet.freeze_panes(1, 0)
                # worksheet.split_panes(15, 8.43)

                # Set the width and align
                worksheet.set_column('A:A', 25, format1)

                # Highlight dif/limit > 5%
                worksheet.conditional_format(1, column_table - 1, row_table, column_table - 1,
                                             {'type': 'cell', 'criteria': '>=',
                                              'value': 0.05, 'format': format_4XXX})
                # Highlight dif/base > 10%
                worksheet.conditional_format(1, column_table, row_table, column_table,
                                             {'type': 'cell', 'criteria': '>=',
                                              'value': 0.1, 'format': format_4XXX})
                for i in range(1, row_table):
                    worksheet.conditional_format(i, 5, i, column_table - 3, {'type': '3_color_scale'})
                worksheet.write_string(row_table + 2, 0, 'Base: ' + file_list[0])
                worksheet.write_string(row_table + 3, 0, 'CMP: ' + file_list[1])
                worksheet.autofilter(0, 0, row_table, column_table)
                self.progress_bar.setValue(97)

                # Write wafer map compare
                wafer_map_cmp = wafer_map_cmp_list[0]
                bin_swap_table = wafer_map_cmp_list[1]
                wafer_map_cmp.to_excel(writer, sheet_name='2 STDF wafer map compare', startrow=0)
                row_table, column_table = wafer_map_cmp.shape
                bin_swap_table.to_excel(writer, sheet_name='2 STDF wafer map compare', startrow=row_table + 2)
                worksheet = writer.sheets['2 STDF wafer map compare']
                worksheet.conditional_format(1, 1, row_table, column_table,
                                             {'type': 'text', 'criteria': 'containing',
                                              'value': '-->', 'format': format_4XXX})
            self.progress_bar.setValue(100)
            self.status_text.setText(
                str(correlation_report_name.split('/')[-1] + " written successfully!"))
        except xlsxwriter.exceptions.FileCreateError:  # PermissionError:
            self.status_text.setText(
                str("Please close " + correlation_report_name.split('/')[-1]))
            self.progress_bar.setValue(0)
        except IndexError:
            self.status_text.setText(
                str("Can not find 2 or more set data in csv file, please check your input!"))
            self.progress_bar.setValue(0)

    def make_correlation_table(self):
        parameters = ['Site', 'Units', 'LowLimit', 'HiLimit']
        file_list = self.df_csv['FILE_NAM'].unique()
        correlation_df = pd.DataFrame()
        if self.file_selected and len(file_list) > 1:
            table_list = []
            for file_name in file_list:
                tmp_df = self.df_csv[self.df_csv.FILE_NAM == file_name]
                table_list.append(self.get_summary_table(tmp_df, self.test_info_list, self.number_of_sites,
                                                         self.list_of_test_numbers, False, True, False))
            hiLimit_df = table_list[0].HiLimit.replace('n/a', 0).astype(float)
            lowlimit_df = table_list[0].LowLimit.replace('n/a', 0).astype(float)

            correlation_df = pd.concat([table_list[0].Site, table_list[0].Units, table_list[0].LowLimit,
                                        table_list[0].HiLimit], axis=1)

            for i in range(len(file_list)):
                correlation_df = pd.concat([correlation_df, table_list[i].Mean.astype('float')], axis=1)
                parameters = parameters + ['Mean(' + file_list[i] + ')']
            correlation_df.columns = parameters
            parameters = parameters + ['Mean Diff(max - min)', 'Mean Diff Over Limit(dif/delta limit)',
                                       'Mean Diff Over Base(dif/first file data)']
            # Add mean delta column
            mean_delta = correlation_df.iloc[:, 4:].max(axis=1) - correlation_df.iloc[:, 4:].min(axis=1)
            mean_delta_over_limit = mean_delta / (hiLimit_df - lowlimit_df)
            # Assume table 0 is the base one
            mean_delta_over_base = mean_delta / table_list[0].Mean.astype(float)
            correlation_df = pd.concat([correlation_df, mean_delta, mean_delta_over_limit, mean_delta_over_base],
                                       axis=1)

            correlation_df.columns = parameters
            # csv_summary_name = str(self.file_path + "_correlation_table.csv")
            #
            # # In case someone has the file open
            # try:
            #     correlation_df.to_csv(path_or_buf=csv_summary_name)
            #     self.status_text.setText(
            #         str(csv_summary_name + " written successfully!"))
            #     self.progress_bar.setValue(100)
            # except PermissionError:
            #     self.status_text.setText(
            #         str("Please close " + csv_summary_name))
            #     self.progress_bar.setValue(0)
        else:
            self.status_text.setText('Please select a csv file with 2 stdf files\' data !!!')
            self.progress_bar.setValue(0)
        return correlation_df, file_list

    def make_wafer_map_cmp(self):
        # Get wafer map
        all_wafer_map_list = []
        file_list = self.df_csv['FILE_NAM'].unique()
        i = 0
        for file in file_list:
            single_file_df = self.df_csv[self.df_csv['FILE_NAM'].isin([file])]
            lot_id_list = single_file_df['LOT_ID'].unique()
            for lot_id in lot_id_list:
                single_lot_df = single_file_df[single_file_df['LOT_ID'].isin([lot_id])]
                wafer_id_list = single_lot_df['WAFER_ID'].unique()
                for wafer_id in wafer_id_list:
                    tmp_wafer_map_list = []
                    single_wafer_df = single_lot_df[single_lot_df['WAFER_ID'].isin([wafer_id])]
                    die_id = str(single_wafer_df['LOT_ID'].iloc[0]) + ' - ' + str(single_wafer_df['WAFER_ID'].iloc[0])
                    wafer_map_df = single_wafer_df.pivot_table(values='SOFT_BIN', index='Y_COORD', columns='X_COORD',
                                                               aggfunc=lambda x: int(tuple(x)[-1]))
                    wafer_map_df.index.name = die_id
                    # Sort Y from low to high
                    wafer_map_df.sort_index(axis=0, ascending=False, inplace=True)
                    tmp_wafer_map_list.append(wafer_map_df)
                    self.progress_bar.setValue(
                        80 + int(i / (len(file_list) + len(lot_id_list) + len(wafer_id_list)) * 10))

            all_wafer_map_list.append(tmp_wafer_map_list)
        cmp_result_list = []
        if len(all_wafer_map_list) >= 2:
            # Compare the First two wafer map in all_wafer_map_list
            base_df = all_wafer_map_list[0][0].fillna(value='')
            cmp_df = all_wafer_map_list[1][0].fillna(value='')
            df1_r, df1_c = base_df.shape
            df2_r, df2_c = cmp_df.shape

            if (df1_r != df2_r) or (df1_c != df2_c):
                result_df = pd.DataFrame({'name': ['Dimension Mismatch of First 2 Wafer Map !!!']})
                axis_df = pd.DataFrame({'name': ['这也没有 !!!']})
                # raise Exception('Dimension Mismatch!')
            else:
                result_df = base_df.copy()
                row_names = result_df.index.values
                col_names = result_df.columns.values
                axis_dic = {'Axis': [], 'Base Bin Number': [], 'CMP Bin Number': []}
                for i in range(df1_c):
                    result_df.iloc[:, i] = np.where(base_df.iloc[:, i] == cmp_df.iloc[:, i],
                                                    base_df.iloc[:, i], base_df.iloc[:, i].astype(str) + '-->' +
                                                    cmp_df.iloc[:, i].astype(str))
                    row_name = row_names[np.where(base_df.iloc[:, i] != cmp_df.iloc[:, i])]
                    col_name = int(col_names[i])
                    if len(row_name) == 0:
                        pass
                    else:
                        for j in row_name:
                            axis_list = [col_name, int(j)]
                            base_bin_num = base_df.loc[j, col_name]
                            cmp_bin_num = cmp_df.loc[j, col_name]

                            axis_dic['Axis'].append(axis_list)
                            axis_dic['Base Bin Number'].append(base_bin_num)
                            axis_dic['CMP Bin Number'].append(cmp_bin_num)
                            self.progress_bar.setValue(
                                90 + int(i / (df1_c + len(row_name)) * 5))
                axis_df = pd.DataFrame.from_dict(axis_dic, orient='index').T
            cmp_result_list = [result_df, axis_df]
        return cmp_result_list

    def generate_s2s_correlation_report(self):
        s2s_correlation_report_name = str(self.file_path + "_s2s_correlation_table.xlsx")
        self.status_text.setText(
            str(s2s_correlation_report_name.split('/')[-1] + " is generating..."))
        self.s2s_correlation_report_df = self.make_s2s_correlation_table()
        self.progress_bar.setValue(95)
        # In case someone has the file open
        try:
            if self.s2s_correlation_report_df.empty:
                self.status_text.setText(
                    str('Only 1 Site Data Found in .csv file !!!'))
                self.progress_bar.setValue(0)
            else:
                with pd.ExcelWriter(s2s_correlation_report_name, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    # Light red fill for Bin 4XXX
                    format_4XXX = workbook.add_format({'bg_color': '#FFC7CE'})
                    # Add width and format for first column
                    format1 = workbook.add_format({'align': 'left'})

                    # Write correlation table
                    self.s2s_correlation_report_df.to_excel(writer, sheet_name='Site2Site correlation table')
                    row_table, column_table = self.s2s_correlation_report_df.shape
                    worksheet = writer.sheets['Site2Site correlation table']
                    worksheet.conditional_format(1, column_table, row_table, column_table,
                                                 {'type': 'cell', 'criteria': '>=',
                                                  'value': 0.05, 'format': format_4XXX})
                    # Freeze pane on the top row
                    worksheet.freeze_panes(1, 0)
                    # Set the width and align
                    worksheet.set_column('A:A', 25, format1)
                    for i in range(1, row_table):
                        worksheet.conditional_format(i, 3, i, column_table - 2, {'type': '3_color_scale'})
                    worksheet.autofilter(0, 0, row_table, column_table)
                    self.progress_bar.setValue(100)
                self.status_text.setText(
                    str(s2s_correlation_report_name.split('/')[-1] + " written successfully!"))
                self.select_s2s_test_menu.setEnabled(True)
                self.generate_heatmap_button.setEnabled(True)
        except xlsxwriter.exceptions.FileCreateError:  # PermissionError:
            self.status_text.setText(
                str("Please close " + s2s_correlation_report_name.split('/')[-1]))
            self.progress_bar.setValue(0)
        pass

    def make_s2s_correlation_table(self):
        correlation_df = pd.DataFrame()
        if self.file_selected:
            table = self.get_summary_table(self.df_csv, self.test_info_list, self.number_of_sites,
                                           self.list_of_test_numbers, False, False, False)
            site_list = table.Site.unique()
            if len(site_list) > 1:
                # Initial table with Hi/Low Limit
                correlation_df = pd.concat(
                    [table[table.Site == site_list[0]].LowLimit, table[table.Site == site_list[0]].HiLimit], axis=1)
                columns = ['LowLimit', 'HiLimit']

                # Add mean value from each site
                for site in site_list:
                    correlation_df = pd.concat([correlation_df, table[table.Site == site].Mean.astype('float')], axis=1)
                    columns = columns + ['Mean(site' + site + ')']

                # Add mean delta column
                mean_delta = correlation_df.iloc[:, 2:].max(axis=1) - correlation_df.iloc[:, 2:].min(axis=1)
                correlation_df = pd.concat([correlation_df, mean_delta], axis=1)
                columns = columns + ['Mean Delta(Max - Min)']

                # Add mean delta over limit column
                hiLimit_df = correlation_df.HiLimit.replace('n/a', 0).astype(float)
                lowlimit_df = correlation_df.LowLimit.replace('n/a', 0).astype(float)
                mean_delta_over_limit = mean_delta / (hiLimit_df - lowlimit_df)
                correlation_df = pd.concat([correlation_df, mean_delta_over_limit], axis=1)
                columns = columns + ['Mean Delta OVer Limit']

                correlation_df.columns = columns
                # csv_summary_name = str(self.file_path + "_correlation_table_s2s.csv")

                return correlation_df
                # # In case someone has the file open
                # try:
                #     correlation_df.to_csv(path_or_buf=csv_summary_name)
                #     self.status_text.setText(
                #         str(csv_summary_name + " written successfully!"))
                #     self.progress_bar.setValue(100)
                # except PermissionError:
                #     self.status_text.setText(
                #         str("Please close " + csv_summary_name + "_correlation.csv"))
                #     self.progress_bar.setValue(0)
            else:
                self.status_text.setText('Only 1 site data found in csv file !!!')
                self.progress_bar.setValue(0)
        else:
            self.status_text.setText('Please select a file')
        return correlation_df

    def make_s2s_correlation_heatmap(self, correlation_df):
        matplotlib.use('qt5Agg')
        self.select_s2s_test_menu.setEnabled(False)
        self.generate_heatmap_button.setEnabled(False)
        self.selected_s2s_tests = self.select_s2s_test_menu.Selectlist()
        s2s_test_list = [x.split(' - ')[1] for x in self.selected_s2s_tests]
        df = correlation_df.iloc[:, 2:-2]
        df = df.loc[s2s_test_list]
        corr_data = df.corr()

        # Plot the heatmap of corr
        fig = plt.figure()  # 分辨率
        ax = fig.add_subplot(111)
        ax.set_yticks(range(len(corr_data.columns)))
        ax.set_yticklabels(corr_data.columns)
        ax.set_xticks(range(len(corr_data.columns)))
        ax.set_xticklabels(corr_data.columns, rotation='vertical')

        im = ax.imshow(corr_data,  # 相关性矩阵数据集
                       cmap='RdYlGn')  # annot默认为False，当annot为True时，在heatmap中每个方格写入数据
        plt.colorbar(im)
        # annotate heatmap
        texts = []
        valfmt = matplotlib.ticker.StrMethodFormatter("{x:.2f}")
        for i in range(corr_data.shape[0]):
            for j in range(corr_data.shape[1]):
                # kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
                text = im.axes.text(j, i, valfmt(corr_data.iloc[i, j]), va='center', ha='center')
                texts.append(text)
        plt.title('Correlogram of Each Site')

        # Plot the trending of eacj site
        fig = plt.figure()
        ax_3d = fig.add_subplot(111, projection='3d')
        ax_3d.set_xlabel("Test Index")
        ax_3d.set_ylabel("Site")
        ax_3d.set_yticks(range(len(df.columns)))
        ax_3d.set_yticklabels(df.columns)
        ax_3d.set_zlabel("Data Value")
        # ax_3d.view_init(90, 0)
        site_num = np.linspace(0, len(df.columns) - 1, len(df.columns))
        row, col = df.shape
        test_index = np.linspace(0, row - 1, row)
        X, Z = np.meshgrid(test_index, site_num)
        for i in range(col):
            Y = df.iloc[:, i].to_list()
            ax_3d.plot(xs=X[i], ys=Y, zs=Z[i], zdir='y')
        plt.title('Trending of Each Site')
        # Adjust the 3D axes scale
        ax_3d.get_proj = lambda: np.dot(Axes3D.get_proj(ax_3d), np.diag([1.2, 1, 1, 1]))
        plt.show()
        self.select_s2s_test_menu.setEnabled(True)
        self.generate_heatmap_button.setEnabled(True)

    def make_subcsv_for_chosen_tests(self):
        sub_csv_name = str(self.file_path[:-11] + "_extract_tests.csv")
        self.selected_subcsv_tests = self.select_test_for_subcsv_menu.Selectlist()
        tmp_df = self.df_csv.iloc[:, :16]
        if len(self.selected_subcsv_tests) >= 1:
            for i in range(len(self.selected_subcsv_tests)):
                tmp_df = pd.concat([tmp_df, self.df_csv[self.selected_subcsv_tests[i]]], axis=1, sort=False, join='outer')

            # Set multiple level columns for csv table
            tname_list = []
            tnumber_list = []
            hilimit_list = []
            lolimit_list = []
            unit_vect_nam_list = []
            tmplist = tmp_df.columns.values.tolist()
            for i in range(len(tmplist)):
                if len(str(tmplist[i]).split(' - ')) == 1:
                    tname_list.append('')
                    tnumber_list.append(str(tmplist[i]))
                    hilimit_list.append('')
                    lolimit_list.append('')
                    unit_vect_nam_list.append('')
                else:
                    # Find the limits
                    tmp_tuple = str(tmplist[i]).split(' - ')
                    low_lim = Backend.get_plot_min(self.test_info_list, tmp_tuple, 0)
                    hi_lim = Backend.get_plot_max(self.test_info_list, tmp_tuple, 0)
                    units = Backend.get_units(self.test_info_list, tmp_tuple, 0)
                    if units.startswith('Unnamed'):
                        units = ''
                    tname_list.append(tmp_tuple[1])
                    tnumber_list.append(tmp_tuple[0])
                    hilimit_list.append(hi_lim)
                    lolimit_list.append(low_lim)
                    unit_vect_nam_list.append(units)
            tmp_df.columns = [tname_list, hilimit_list, lolimit_list, unit_vect_nam_list, tnumber_list]
            # In case file is open
            try:
                tmp_df.to_csv(sub_csv_name, index=False)
                self.status_text.setText(
                    str(sub_csv_name.split('/')[-1] + " written successfully!"))
                self.progress_bar.setValue(100)
            except PermissionError:
                self.status_text.setText(
                    str("Please close " + sub_csv_name.split('/')[-1]))
                self.progress_bar.setValue(0)
        else:
            self.status_text.setText('Please select one or more tests and try again!')
            self.progress_bar.setValue(0)

    # Get the summary results for all sites/each site in each test
    def get_summary_table(self, all_test_data, test_info_list, num_of_sites, test_list, merge_sites, output_them_both, print_data):

        parameters = ['Site', 'Units', 'Runs', 'Fails', 'LowLimit', 'HiLimit',
                      'Min', 'Mean', 'Max', 'Range', 'STD', 'Cp', 'Cpl', 'Cpu', 'Cpk']

        summary_results = []

        df_csv = all_test_data

        sdr_parse = self.sdr_parse

        # Extract test data per site for later usage, to improve time performance
        if (not merge_sites) or output_them_both:
            # parameters[0] = 'Site'
            site_test_data_dic = {}
            for j in sdr_parse:
                site_test_data_dic[str(j)] = df_csv[df_csv.SITE_NUM == j]

        for i in range(0, len(test_list)):
            # merge all sites data
            all_data_array = df_csv.iloc[:, i + 16].to_numpy()
            ## Get rid of all no-string value to NaN, and replace to None
            # all_data_array = pd.to_numeric(df_csv.iloc[:, i + 12], errors='coerce').to_numpy()
            all_data_array = all_data_array[~np.isnan(all_data_array)]

            ## Get rid of (F) and conver to float on series
            # all_data_array = df_csv.iloc[:, i + 12].str.replace(r'\(F\)', '').astype(float).to_numpy()

            units = Backend.get_units(test_info_list, test_list[i], num_of_sites)

            minimum = Backend.get_plot_min(test_info_list, test_list[i], num_of_sites)

            maximum = Backend.get_plot_max(test_info_list, test_list[i], num_of_sites)

            if merge_sites or output_them_both:
                summary_results.append(Backend.site_array(
                    all_data_array, minimum, maximum, 'ALL', units))
            if (not merge_sites) or output_them_both:
                for j in sdr_parse:
                    site_test_data_df = site_test_data_dic[str(j)]
                    site_test_data = site_test_data_df.iloc[:, i + 16].to_numpy()

                    ## Get rid of (F) and conver to float on series
                    # site_test_data = pd.to_numeric(site_test_data_df.iloc[:, i + 12], errors='coerce').to_numpy()
                    # Series.dropna() can remove NaN, but slower than numpy.isnan
                    site_test_data = site_test_data[~np.isnan(site_test_data)]
                    # Add loop data in analysis report
                    if print_data: #'_LOOP' in self.file_path.upper():
                        summary_results.append(Backend.site_array(
                            site_test_data, minimum, maximum, j, units) + site_test_data.tolist())
                    else:
                        summary_results.append(Backend.site_array(
                            site_test_data, minimum, maximum, j, units))
            self.progress_bar.setValue(20 + int(i / len(test_list) * 50))
        test_names = []

        for i in range(0, len(test_list)):
            # add for split multi-site
            if merge_sites or output_them_both:
                test_names.append(test_list[i][1])
            if (not merge_sites) or output_them_both:
                for j in range(0, len(sdr_parse)):
                    test_names.append(test_list[i][1])

            self.progress_bar.setValue(70 + int(i / len(test_list) * 10))

        if print_data: #'_LOOP' in self.file_path.upper():
            for i in range(0, len(summary_results[1]) - 15):
                parameters += ['LOOP' + str(i)]

        table = pd.DataFrame(
            summary_results, columns=parameters, index=test_names)

        self.progress_bar.setValue(80)

        return table

    # Given a set of data for each test, the full set of ptr data, the number of sites, and the list of names/tests
    # for the set of data needed, expect each item in this set of data to be plotted in a new figure test_info_list
    # should be an array of arrays of arrays with the same length as test_list, which is an array of tuples with each
    # tuple representing the test number and name of the test data in that specific trial
    def plot_list_of_tests(self):
        matplotlib.use('Agg')
        if self.file_selected:

            self.generate_pdf_button.setEnabled(False)
            self.select_test_menu.setEnabled(False)
            self.limit_toggle.setEnabled(False)
            self.selected_tests = self.select_test_menu.Selectlist()
            self.threaded_task = PdfWriterThread(file_path=self.file_path, all_data=self.df_csv,
                                                 ptr_data=self.test_info_list,
                                                 number_of_sites=self.number_of_sites,
                                                 selected_tests=self.selected_tests, limits_toggled=self.limits_toggled,
                                                 list_of_test_numbers=self.list_of_test_numbers,
                                                 site_list=self.sdr_parse, group_by_file=self.group_toggled)

            self.threaded_task.notify_progress_bar.connect(self.on_progress)
            self.threaded_task.notify_status_text.connect(self.on_update_text)
            self.threaded_task.finished.connect(self.restore_menu)
            self.threaded_task.start()

            # self.generate_pdf_button.setEnabled(False)
            # self.select_test_menu.setEnabled(False)
            # self.limit_toggle.setEnabled(False)
            self.main_window()
        else:

            self.status_text.setText('Please select a file')

    def plot_list_of_tests_on_one_figure(self):
        matplotlib.use('qt5Agg')
        # self.number_of_sites
        # self.sdr_parse
        self.selected_tests = self.select_test_menu.Selectlist()
        # self.test_info_list

        site_test_data_dic = {}
        for i in self.sdr_parse:
            site_test_data_dic[str(i)] = self.df_csv[self.df_csv.SITE_NUM == i]
        plt.figure()
        for i in range(len(self.selected_tests)):
            site_test_data_list = []
            label_list = []
            for j in self.sdr_parse:
                site_test_data = site_test_data_dic[str(j)][self.selected_tests[i]].to_numpy()
                tmp_site_test_data_list = site_test_data[~np.isnan(site_test_data)].tolist()
                ## Ignore fail value
                # site_test_data = pd.to_numeric(site_test_data_dic[str(j)].iloc[:, i - 1 + 12],
                #                                errors='coerce').dropna().values.tolist()
                site_test_data_list.append(tmp_site_test_data_list)
                label_list.append(str(j)+ ' - ' + self.selected_tests[i].split(' - ')[-1])
            all_data_array = site_test_data_list

            units = Backend.get_units(self.test_info_list, self.selected_tests[i].split(' - '), self.number_of_sites)

            # Plots each site one at a time
            for i in range(0, len(all_data_array)):
                Backend.plot_single_site_trend(all_data_array[i], False, label_list, i)
        plt.legend()
        plt.xlabel("Trials")
        plt.ylabel(units)
        plt.title("Trendline")
        plt.grid(color='0.9', linestyle='--', linewidth=1)
        plt.show()

    def restore_menu(self):
        self.generate_pdf_button.setEnabled(True)
        self.select_test_menu.setEnabled(True)
        self.limit_toggle.setEnabled(True)

    def on_progress(self, i):
        self.progress_bar.setValue(i)

    def on_update_text(self, txt):
        self.status_text.setText(txt)


class ComboCheckBox(QComboBox):
    popupAboutToBeShown = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=None)
        self.qListWidget = QListWidget()
        self.qLineEdit = QLineEdit()
        self.qCheckBox = []
        self.Selectedrow_num = 0
        self.items = []
        self.row_num = 0
        self.popupAboutToBeShown.connect(self.regex_select)

    def loadItems(self, items):
        self.items = ['ALL DATA'] + items
        # self.items.insert(0, 'ALL DATA')
        self.row_num = len(self.items)

        self.qListWidget = QListWidget()
        self.qLineEdit = QLineEdit()
        self.qCheckBox = []
        self.Selectedrow_num = 0

        # self.qLineEdit.setReadOnly(True)
        self.addQCheckBox(0)
        self.qCheckBox[0].stateChanged.connect(self.All)
        for i in range(1, self.row_num):
            self.addQCheckBox(i)
            self.qCheckBox[i].stateChanged.connect(self.showMessage)
        self.setModel(self.qListWidget.model())
        self.setView(self.qListWidget)
        self.setLineEdit(self.qLineEdit)
        # self.qLineEdit.textChanged.connect(self.printResults)

    # Re-write showPopup method, to avoid the incomplete display when too many items
    def showPopup(self):
        self.popupAboutToBeShown.emit()
        # Select current items
        select_list = self.Selectlist()
        # Reload the items
        self.loadItems(items=self.items[1:])
        for i in range(1, self.row_num):
            self.qCheckBox[i].stateChanged.disconnect()
        for select in select_list:
            index = self.items[:].index(select)
            # Check the items
            self.qCheckBox[index].setChecked(True)
        for i in range(1, self.row_num):
            self.qCheckBox[i].stateChanged.connect(self.showMessage)
        self.showMessage()
        return QComboBox.showPopup(self)

    def addQCheckBox(self, i):
        self.qCheckBox.append(QCheckBox())
        qItem = QListWidgetItem(self.qListWidget)
        self.qCheckBox[i].setText(self.items[i])
        self.qListWidget.setItemWidget(qItem, self.qCheckBox[i])

    def Selectlist(self):
        Outputlist = [ch.text() for ch in self.qCheckBox[1:] if ch.isChecked()]
        self.Selectedrow_num = len(Outputlist)
        return Outputlist

    def showMessage(self):
        # self.qLineEdit.setReadOnly(False)
        self.qLineEdit.clear()
        Outputlist = self.Selectlist()

        if self.Selectedrow_num == 0:
            # Clear, nothing is selected
            self.qCheckBox[0].setCheckState(0)
            show = ''
        elif self.Selectedrow_num == self.row_num - 1:
            # All are selected
            self.qCheckBox[0].setCheckState(2)
            show = 'ALL DATA'
        else:
            # Part is/are selected
            self.qCheckBox[0].setCheckState(1)
            show = ';'.join(Outputlist)
        self.qLineEdit.setText(show)
        # self.qLineEdit.setReadOnly(True)

    def All(self, check_state):
        # disconnect 'showMessage' to improve time performance
        for i in range(1, self.row_num):
            self.qCheckBox[i].stateChanged.disconnect()
        if check_state == 2:
            for i in range(1, self.row_num):
                self.qCheckBox[i].setChecked(True)
            self.showMessage()
        elif check_state == 1:
            if self.Selectedrow_num == 0:
                self.qCheckBox[0].setCheckState(2)
        elif check_state == 0:
            self.clear()
            self.showMessage()
        for i in range(1, self.row_num):
            self.qCheckBox[i].stateChanged.connect(self.showMessage)

    def regex_select(self):
        text = self.qLineEdit.text()
        new_tests_list = []  # 保存筛选出来log的列表
        tests_index_list = []
        try:
            if text != '':
                for index, data in enumerate(self.items[1:]):  # 遍历列表
                    if re.match(text, data) != None:  # 如果正则匹配出的数据不为None, 就将此数据添加到新列表中
                        new_tests_list.append(data)
                        tests_index_list.append(index)
                if len(tests_index_list) != 0:
                    self.clear()
                    for i in range(1, self.row_num):
                        self.qCheckBox[i].stateChanged.disconnect()
                    for i in tests_index_list:
                        self.qCheckBox[i + 1].setChecked(True)
                    for i in range(1, self.row_num):
                        self.qCheckBox[i].stateChanged.connect(self.showMessage)
                    self.showMessage()
        except re.error:
            pass
        # new_tests_list = list(filter(lambda x: re.match(text, x) != None, self.items[1:]))
        print(new_tests_list)
        if len(tests_index_list) != 0:
            logging.info('Debug message: ' + ', '.join(
                new_tests_list))  # .error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        else:
            logging.info('Debug message: ' + 'No Test Instances Found.')
        pass

    def clear(self):
        for i in range(self.row_num):
            self.qCheckBox[i].setChecked(False)


class MyExceptHook(ABC):
    @staticmethod
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        sys.exit(0)


# Execute me
if __name__ == '__main__':
    # initialize the log settings
    if getattr(sys, 'frozen', False):
        pathname = os.path.dirname(sys.executable)
    else:
        pathname = os.path.dirname(__file__)
    logging.basicConfig(filename=pathname + '\\app.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    sys.excepthook = MyExceptHook.handle_exception
    app = QApplication(sys.argv)
    nice = Application()
    sys.exit(app.exec_())
