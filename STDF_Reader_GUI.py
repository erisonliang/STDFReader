# -*- coding:utf-8 -*-
###################################################
# STDF Reader GUI                                 #
# Version: Beta 0.3                               #
#                                                 #
# Sep. 18, 2019                                   #
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

# from numba import jit
from src.Backend import Backend
from src.FileRead import FileReaders
from src.Threads import PdfWriterThread, CsvParseThread, XlsxParseThread

Version = 'Beta 0.4.1'


###################################################

########################
# QT GUI FUNCTIONALITY #
########################

# Object oriented programming should be illegal cus i forgot how to be good at it
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

        exitAct = QAction(QIcon('exit.png'), '&Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.triggered.connect(qApp.quit)
        aboutAct = QAction(QIcon('about.png'), '&About', self)
        aboutAct.triggered.connect(self.aboutecho)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        helpMenu = menubar.addMenu('&Help')
        fileMenu.addAction(exitAct)
        helpMenu.addAction(aboutAct)

        self.status_text = QLabel()
        self.status_text.setText('Welcome!')

        # Button to parse to .txt
        self.stdf_upload_button_xlsx = QPushButton('Parse STD/STDF to .xlsx table (very slow)')
        self.stdf_upload_button_xlsx.setToolTip(
            'Browse for a file ending in .std to create a parsed .xlsx file')
        self.stdf_upload_button_xlsx.clicked.connect(self.open_parsing_dialog_xlsx)

        # Button to parse to .csv
        self.stdf_upload_button = QPushButton(
            'Parse STD/STDF to .csv log')
        self.stdf_upload_button.setToolTip(
            'Browse for stdf to create .csv file. This is helpful when doing data analysis')
        self.stdf_upload_button.clicked.connect(
            self.open_parsing_dialog_csv)

        # Button to upload the .txt file to work with
        self.txt_upload_button = QPushButton('Upload parsed .csv file')
        self.txt_upload_button.setToolTip(
            'Browse for the .csv file containing the parsed STDF data')
        self.txt_upload_button.clicked.connect(self.open_text)

        # Generates a summary of the loaded text
        self.generate_summary_button = QPushButton(
            'Generate data analysis report')
        self.generate_summary_button.setToolTip(
            'Generate a .xlsx data analysis report for the uploaded parsed .csv')
        self.generate_summary_button.clicked.connect(self.generate_analysis_report)

        # Selects a test result for the desired
        self.select_test_menu = ComboCheckBox()  # ComboCheckBox() # QComboBox()
        self.select_test_menu.setToolTip(
            'Select the tests to produce the PDF results for')

        # Button to generate the test results for the desired tests from the selected menu
        self.generate_pdf_button = QPushButton(
            'Generate .pdf from selected tests')
        self.generate_pdf_button.setToolTip(
            'Generate a .pdf file with the selected tests from the parsed .txt')
        self.generate_pdf_button.clicked.connect(self.plot_list_of_tests)

        self.limit_toggle = QCheckBox('Plot against failure limits', self)
        self.limit_toggle.setChecked(True)
        self.limit_toggle.stateChanged.connect(self.toggler)
        self.limits_toggled = True

        # Generates a correlation report for all sites of the loaded data
        self.generate_correlation_button = QPushButton(
            'Generate correlation report of 2 stdf files')
        self.generate_correlation_button.setToolTip(
            'Generate a .xlsx correlation report of 2 stdf files for the uploaded parsed .csv')
        self.generate_correlation_button.clicked.connect(self.generate_correlation_report)

        # Generates a correlation report for site2site compare
        self.generate_correlation_button_s2s = QPushButton(
            'Generate correlation of Site2Site')
        self.generate_correlation_button_s2s.setToolTip(
            'Generate an Site2Site correlation report')
        self.generate_correlation_button_s2s.clicked.connect(self.make_s2s_correlation_table)

        # Generates a wafer map comparison
        self.generate_wafer_cmp_button = QPushButton(
            'Generate wafer map comparison stdf files')
        self.generate_wafer_cmp_button.setToolTip(
            'Generate a wafer map comparison .csv for correlation')
        self.generate_wafer_cmp_button.clicked.connect(self.make_wafer_map_cmp)

        self.progress_bar = QProgressBar()

        self.WINDOW_SIZE = (700, 280)
        self.file_path = None
        self.text_file_location = self.file_path

        self.setFixedSize(self.WINDOW_SIZE[0], self.WINDOW_SIZE[1])
        self.center()
        self.setWindowTitle('STDF Reader For AP ' + Version)

        self.test_text = QLabel()
        self.test_text.setText("test")

        self.selected_tests = []

        self.file_selected = False

        self.threaded_task = PdfWriterThread(file_path=self.file_path, all_data=self.df_csv,
                                             ptr_data=self.test_info_list, number_of_sites=self.number_of_sites,
                                             selected_tests=self.selected_tests, limits_toggled=self.limits_toggled,
                                             list_of_test_numbers=self.list_of_test_numbers, site_list=self.sdr_parse)

        self.threaded_task.notify_progress_bar.connect(self.on_progress)
        self.threaded_task.notify_status_text.connect(self.on_update_text)

        self.threaded_csv_parser = CsvParseThread(file_path=self.file_path)
        self.threaded_csv_parser.notify_status_text.connect(
            self.on_update_text)

        self.threaded_xlsx_parser = XlsxParseThread(file_path=self.file_path)
        self.threaded_xlsx_parser.notify_status_text.connect(
            self.on_update_text)

        self.generate_pdf_button.setEnabled(False)
        self.select_test_menu.setEnabled(False)
        self.generate_summary_button.setEnabled(False)
        self.limit_toggle.setEnabled(False)
        self.generate_correlation_button.setEnabled(False)
        self.generate_correlation_button_s2s.setEnabled(False)
        self.generate_wafer_cmp_button.setEnabled(False)

        self.main_window()

    # Tab for data analysis
    def tab_data_analysis(self):
        layout = QGridLayout()
        layout.addWidget(self.generate_summary_button, 0, 0, 1, 2)
        layout.addWidget(self.select_test_menu, 1, 0, 1, 2)
        layout.addWidget(self.generate_pdf_button, 2, 0)
        layout.addWidget(self.limit_toggle, 2, 1)
        self.data_analysis_tab.setLayout(layout)

    # Tab for data correlation
    def tab_data_correlation(self):
        layout = QGridLayout()
        layout.addWidget(self.generate_correlation_button, 0, 0)
        layout.addWidget(self.generate_correlation_button_s2s, 0, 1)
        self.correlation_tab.setLayout(layout)

    # Main interface method
    def main_window(self):
        # self.setGeometry(300, 300, 300, 200)
        # self.resize(900, 700)
        self.setWindowTitle('STDF Reader For AP ' + Version)

        # Layout
        layout = QGridLayout()
        self.setLayout(layout)

        # Adds the widgets together in the grid
        layout.addWidget(self.status_text, 0, 0, 1, 2)
        layout.addWidget(self.stdf_upload_button_xlsx, 1, 0)
        layout.addWidget(self.stdf_upload_button, 1, 1)
        layout.addWidget(self.txt_upload_button, 2, 0, 1, 2)

        tabs = QTabWidget(self)
        self.data_analysis_tab = QWidget()
        self.correlation_tab = QWidget()
        self.tab_data_analysis()
        self.tab_data_correlation()
        tabs.addTab(self.data_analysis_tab, 'Data Analysis')
        tabs.addTab(self.correlation_tab, 'Data Correlation')
        layout.addWidget(tabs, 3, 0, 1, 2)

        # layout.addWidget(self.generate_summary_button, 3, 0)  # , 1, 2)
        # layout.addWidget(self.generate_summary_button_split, 3, 1)
        # layout.addWidget(self.select_test_menu, 4, 0, 1, 2)
        # layout.addWidget(self.generate_pdf_button, 5, 0)
        # layout.addWidget(self.limit_toggle, 5, 1)
        layout.addWidget(self.progress_bar, 6, 0, 1, 2)

        # 创建一个 QWidget ，并将其布局设置为 layout_grid ：
        widget = QWidget()
        widget.setLayout(layout)
        # 将 widget 设为主窗口的 central widget ：
        self.setCentralWidget(widget)

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

    # Opens and reads a file to parse the data
    def open_parsing_dialog(self):

        # self.threaded_text_parser.start()
        #
        # self.main_window()

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
        # I can not figure out the process when parse STDF, so...
        self.progress_bar.setMinimum(0)

        # Move QFileDialog out of QThread, in case of error under win 7
        self.status_text.setText('Parsing to .csv file, please wait...')
        filterboi = 'STDF (*.stdf *.std)'
        filepath = QFileDialog.getOpenFileNames(
            caption='Open STDF File', filter=filterboi)

        self.status_text.update()
        self.stdf_upload_button.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.threaded_csv_parser = CsvParseThread(filepath)
        self.threaded_csv_parser.notify_status_text.connect(self.on_update_text)
        self.threaded_csv_parser.finished.connect(self.set_progress_bar_max)
        self.threaded_csv_parser.start()
        self.stdf_upload_button.setEnabled(True)
        self.main_window()

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
        self.main_window()

    def set_progress_bar_max(self):
        self.progress_bar.setMaximum(100)

    # Checks if the toggle by limits mark is checked or not
    def toggler(self, state):

        if state == Qt.Checked:
            self.limits_toggled = True
        else:
            self.limits_toggled = False

    # Opens and reads a file to parse the data. Much of this is what was done in main() from the text version
    def open_text(self):

        # Change to allow to upload file without restart program
        if True:  # self.file_selected:
            # Only accepts text files
            filterboi = 'CSV Table (*.csv)'
            filepath = QFileDialog.getOpenFileName(
                caption='Open .csv File', filter=filterboi)

            self.file_path = filepath[0]

            # Because you can open it and select nothing smh
            if self.file_path != '':

                # self.txt_upload_button.setEnabled(False)

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
                    self.single_columns = tmp_pd.get_level_values(4).values.tolist()[:17]  # Get the part info
                    self.tnumber_list = tmp_pd.get_level_values(4).values.tolist()[17:]
                    self.tname_list = tmp_pd.get_level_values(0).values.tolist()[17:]
                    self.test_info_list = tmp_pd.values.tolist()[17:]
                    self.list_of_test_numbers_string = [j + ' - ' + i for i, j in
                                                        zip(self.tname_list, self.tnumber_list)]
                    # Change the multi-level columns to single level columns
                    self.single_columns = self.single_columns + self.list_of_test_numbers_string
                    self.df_csv.columns = self.single_columns

                    # Data cleaning, get rid of '(F)'
                    self.df_csv.replace(r'\(F\)', '', regex=True, inplace=True)
                    self.df_csv.iloc[:, 17:] = self.df_csv.iloc[:, 17:].astype('float')
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
                # sdr_parse = self.sdr_data[0].split("|")

                self.progress_bar.setValue(35)

                self.file_selected = True

                self.select_test_menu.loadItems(
                    self.list_of_test_numbers_string)

                self.selected_tests = []

                # log parsed document, if duplicate test number exist, show warning !
                if len(self.list_of_duplicate_test_numbers) > 0:
                    self.status_text.setText(
                        'Parsed .csv uploaded! But Duplicate Test Number Found! Please Check \'duplicate_test_number.csv\'')
                else:
                    self.status_text.setText('Parsed .csv uploaded!')

                self.progress_bar.setValue(100)

                self.generate_pdf_button.setEnabled(True)
                self.select_test_menu.setEnabled(True)
                self.generate_summary_button.setEnabled(True)
                self.limit_toggle.setEnabled(True)
                self.generate_correlation_button.setEnabled(True)
                self.generate_correlation_button_s2s.setEnabled(True)
                self.generate_wafer_cmp_button.setEnabled(True)
                self.main_window()

            else:

                self.status_text.setText('Please select a file')

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

    def generate_analysis_report(self):
        analysis_report_name = str(self.file_path[:-11] + "_analysis_report.xlsx")
        self.status_text.setText(
            str(analysis_report_name + " is generating..."))

        startt = time.time()
        data_summary = self.make_data_summary_report()
        endt = time.time()
        print('data summary Time: ', endt - startt)

        startt = time.time()
        duplicate_number_report = self.make_duplicate_num_report()
        self.progress_bar.setValue(82)
        endt = time.time()
        print('duplicate number Time: ', endt - startt)

        startt = time.time()
        bin_summary_list = self.make_bin_summary()
        self.progress_bar.setValue(85)
        endt = time.time()
        print('bin summary Time: ', endt - startt)

        startt = time.time()
        wafer_map_list = self.make_wafer_map()
        self.progress_bar.setValue(88)
        endt = time.time()
        print('wafer map Time: ', endt - startt)

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

                data_summary.to_excel(writer, sheet_name='Data Stastics')
                row_table, column_table = data_summary.shape
                worksheet = writer.sheets['Data Stastics']
                worksheet.conditional_format(1, column_table - 1, row_table, column_table - 1,
                                             {'type': 'cell', 'criteria': '<',
                                              'value': 3.3, 'format': format_4XXX})
                worksheet.conditional_format(1, column_table, row_table, column_table,
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
                        if i == 0 and j == 0:
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

            table = self.get_summary_table(self.df_csv, self.test_info_list, self.number_of_sites,
                                           self.list_of_test_numbers, True, True)

            self.progress_bar.setValue(80)

            # csv_summary_name = str(self.file_path[:-11] + "_data_summary.csv")
            #
            # # In case someone has the file open
            # try:
            #     table.to_csv(path_or_buf=csv_summary_name)
            #     self.status_text.setText(
            #         str(csv_summary_name + " written successfully!"))
            #     self.progress_bar.setValue(100)
            # except PermissionError:
            #     self.status_text.setText(
            #         str("Please close " + csv_summary_name + "_data_summary.csv"))
            #     self.progress_bar.setValue(0)
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
        log_csv = pd.DataFrame()
        if len(self.list_of_duplicate_test_numbers) > 0:
            log_csv = pd.DataFrame(self.list_of_duplicate_test_numbers,
                                   columns=['Test Number', 'Test Name', 'Test Name'])
            # try:
            #     log_csv.to_csv(path_or_buf=str(
            #         self.file_path[:-11].split('/')[-1] + "_duplicate_test_number.csv"))
            # except PermissionError:
            #     self.status_text.setText(
            #         str(
            #             "Please close duplicate_test_number.csv file to generate a new one !!!"))

        return log_csv

    def make_bin_summary(self):
        all_bin_summary_list = []
        lot_id_list = self.df_csv['LOT_ID'].unique()
        for lot_id in lot_id_list:
            wafer_id_list = self.df_csv['WAFER_ID'].unique()
            for wafer_id in wafer_id_list:
                single_wafer_df = self.df_csv[self.df_csv['LOT_ID'].isin([lot_id]) &
                                              self.df_csv['WAFER_ID'].isin([wafer_id])]
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

                # Write correlation table
                correlation_table.to_excel(writer, sheet_name='2 STDF correlation table')
                row_table, column_table = correlation_table.shape
                worksheet = writer.sheets['2 STDF correlation table']
                worksheet.conditional_format(1, column_table, row_table, column_table,
                                             {'type': 'cell', 'criteria': '>=',
                                              'value': 0.05, 'format': format_4XXX})
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

    def make_correlation_table(self):
        parameters = ['Site', 'Units', 'LowLimit', 'HiLimit', 'Mean(base)',
                      'Mean(cmp)', 'Mean Diff(base - cmp)', 'Mean Diff Over Limit']
        file_list = self.df_csv['FILE_NAM'].unique()
        correlation_df = pd.DataFrame()
        if self.file_selected and len(file_list) > 1:
            table_list = []
            for file_name in file_list:
                tmp_df = self.df_csv[self.df_csv.FILE_NAM == file_name]
                table_list.append(self.get_summary_table(tmp_df, self.test_info_list, self.number_of_sites,
                                                         self.list_of_test_numbers, False, True))
            mean_delta = table_list[0].Mean.astype(float) - table_list[1].Mean.astype(float)
            hiLimit_df = table_list[0].HiLimit.replace('n/a', 0).astype(float)
            lowlimit_df = table_list[0].LowLimit.replace('n/a', 0).astype(float)
            mean_delta_over_limit = mean_delta / (hiLimit_df - lowlimit_df)

            correlation_df = pd.concat([table_list[0].Site, table_list[0].Units, table_list[0].LowLimit,
                                        table_list[0].HiLimit, table_list[0].Mean, table_list[1].Mean, mean_delta,
                                        mean_delta_over_limit], axis=1)
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

    def make_s2s_correlation_table(self):
        if self.file_selected:
            table = self.get_summary_table(self.df_csv, self.test_info_list, self.number_of_sites,
                                           self.list_of_test_numbers, False, False)
            site_list = table.Site.unique()
            if len(site_list) > 1:
                correlation_df = pd.concat(
                    [table[table.Site == site_list[0]].LowLimit, table[table.Site == site_list[0]].HiLimit], axis=1)
                columns = ['LowLimit', 'HiLimit']
                for site in site_list:
                    correlation_df = pd.concat([correlation_df, table[table.Site == site].Mean], axis=1)
                    columns = columns + ['Mean(site' + site + ')']
                correlation_df.columns = columns
                csv_summary_name = str(self.file_path + "_correlation_table_s2s.csv")

                # In case someone has the file open
                try:
                    correlation_df.to_csv(path_or_buf=csv_summary_name)
                    self.status_text.setText(
                        str(csv_summary_name + " written successfully!"))
                    self.progress_bar.setValue(100)
                except PermissionError:
                    self.status_text.setText(
                        str("Please close " + csv_summary_name + "_correlation.csv"))
                    self.progress_bar.setValue(0)
            else:
                self.status_text.setText('Only 1 site data found in csv file !!!')
                self.progress_bar.setValue(0)
        else:
            self.status_text.setText('Please select a file')

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
                col_name = col_names[i]
                for j in row_name:
                    axis_list = [col_name, j]
                    base_bin_num = base_df.loc[j, col_name]
                    cmp_bin_num = cmp_df.loc[j, col_name]
                    self.progress_bar.setValue(
                        90 + int(i / (df1_c + len(row_name)) * 5))
                axis_dic['Axis'].append(axis_list)
                axis_dic['Base Bin Number'].append(base_bin_num)
                axis_dic['CMP Bin Number'].append(cmp_bin_num)
            axis_df = pd.DataFrame.from_dict(axis_dic, orient='index').T
        cmp_result_list = [result_df, axis_df]
        return cmp_result_list

    # Get the summary results for all sites/each site in each test
    def get_summary_table(self, all_test_data, test_info_list, num_of_sites, test_list, merge_sites, output_them_both):

        parameters = ['Site', 'Units', 'Runs', 'Fails', 'LowLimit', 'HiLimit',
                      'Min', 'Mean', 'Max', 'Range', 'STD', 'Cp', 'Cpk']

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
            all_data_array = df_csv.iloc[:, i + 17].to_numpy()
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
                    site_test_data = site_test_data_df.iloc[:, i + 17].to_numpy()

                    ## Get rid of (F) and conver to float on series
                    # site_test_data = pd.to_numeric(site_test_data_df.iloc[:, i + 12], errors='coerce').to_numpy()
                    # Series.dropna() can remove NaN, but slower than numpy.isnan
                    site_test_data = site_test_data[~np.isnan(site_test_data)]
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

        table = pd.DataFrame(
            summary_results, columns=parameters, index=test_names)

        self.progress_bar.setValue(80)

        return table

    # Given a set of data for each test, the full set of ptr data, the number of sites, and the list of names/tests
    # for the set of data needed, expect each item in this set of data to be plotted in a new figure test_info_list
    # should be an array of arrays of arrays with the same length as test_list, which is an array of tuples with each
    # tuple representing the test number and name of the test data in that specific trial
    def plot_list_of_tests(self):

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
                                                 site_list=self.sdr_parse)

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

    def restore_menu(self):
        self.generate_pdf_button.setEnabled(True)
        self.select_test_menu.setEnabled(True)
        self.limit_toggle.setEnabled(True)

    def on_progress(self, i):
        self.progress_bar.setValue(i)

    def on_update_text(self, txt):
        self.status_text.setText(txt)


class ComboCheckBox(QComboBox):
    def loadItems(self, items):
        self.items = items
        self.items.insert(0, 'ALL DATA')
        self.row_num = len(self.items)
        self.Selectedrow_num = 0
        self.qCheckBox = []
        self.qLineEdit = QLineEdit()
        self.qLineEdit.setReadOnly(True)
        self.qListWidget = QListWidget()
        self.addQCheckBox(0)
        self.qCheckBox[0].stateChanged.connect(self.All)
        for i in range(1, self.row_num):
            self.addQCheckBox(i)
            self.qCheckBox[i].stateChanged.connect(self.showMessage)
        self.setModel(self.qListWidget.model())
        self.setView(self.qListWidget)
        self.setLineEdit(self.qLineEdit)
        # self.qLineEdit.textChanged.connect(self.printResults)

    def showPopup(self):
        #  重写showPopup方法，避免下拉框数据多而导致显示不全的问题
        # select_list = self.Selectlist()  # 当前选择数据
        # self.loadItems(items=self.items[1:])  # 重新添加组件
        # for select in select_list:
        #     index = self.items[:].index(select)
        #     self.qCheckBox[index].setChecked(True)  # 选中组件
        return QComboBox.showPopup(self)

    def addQCheckBox(self, i):
        self.qCheckBox.append(QCheckBox())
        qItem = QListWidgetItem(self.qListWidget)
        self.qCheckBox[i].setText(self.items[i])
        self.qListWidget.setItemWidget(qItem, self.qCheckBox[i])

    def Selectlist(self):
        Outputlist = [ch.text() for ch in self.qCheckBox[1:] if ch.isChecked()]
        # for i in range(1, self.row_num):
        #     if self.qCheckBox[i].isChecked():
        #         Outputlist.append(self.qCheckBox[i].text())
        self.Selectedrow_num = len(Outputlist)
        return Outputlist

    def showMessage(self):
        self.qLineEdit.setReadOnly(False)
        self.qLineEdit.clear()
        Outputlist = self.Selectlist()

        if self.Selectedrow_num == 0:
            self.qCheckBox[0].setCheckState(0)  # Clear, nothing is selected
            show = ''
        elif self.Selectedrow_num == self.row_num - 1:
            self.qCheckBox[0].setCheckState(2)  # All are selected
            show = 'ALL DATA'
        else:
            self.qCheckBox[0].setCheckState(1)  # Part is/are selected
            show = ';'.join(Outputlist)
        self.qLineEdit.setText(show)
        self.qLineEdit.setReadOnly(True)

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
    logging.basicConfig(filename=pathname + '\\app.log', level=logging.ERROR,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    sys.excepthook = MyExceptHook.handle_exception
    app = QApplication(sys.argv)
    nice = Application()
    sys.exit(app.exec_())
