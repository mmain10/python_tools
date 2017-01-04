#!/usr/bin/python
import csv
import os
import sys
import shutil
import datetime as dt


class CSVCleaner:

    """
    The CSVCleaner object provides an easy interface to clean csvs with the given interface

    To configure a CSVCleaner object, pass the csv_filepath along with fieldnames (in order) for the header fields\
    The CSVCleaner always performs operations on THE SAME CSV unless given "copy=False"

    Usage follows like:
    >>> csv_cleaner = CSVCleaner('./tests/test_csv.csv')
    """

    def __init__(self, filepath, fieldnames, header=True):
        """
        :param filepath: a path to the csv
        :param fieldnames: an iterable of the fieldnames for each collumn of the csv
        """

        self.input_filename = filepath
        self.fieldnames = fieldnames
        self.has_header = header
        self.file_name = filepath.split('/')[-1]
        self.working_dir = '/'.join(filepath.split('/')[:-1]) + '/'
        self.temp_filename = self.working_dir + 'CSVCleaners_temp.csv'

    def initialize_reader(self):
        with open(self.input_filename, 'r') as input_file:
            reader = csv.DictReader(input_file, fieldnames=self.fieldnames)

            yield [row for row in reader]

    def initialize_writer(self):
        with open(self.temp_filename, 'w') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=self.fieldnames)
            writer.writeheader()

            return writer

    @staticmethod
    def convert_datetime(date, input_format, output_format):
        return dt.datetime.strptime(date, input_format).strftime(output_format)

    def process_date_field(self, input_dict, field, input_format, output_format):
        """
        Wrapper method for processing dicts with datetime objects
        :param input_dict: dictionary of input data
        :param field: field to process
        :param input_format: format given
        :param output_format: format to output
        :return: formatted version of input_dict
        """
        output_dict = input_dict.copy()

        if output_dict[field] is None:
            return output_dict
        elif output_dict[field].casefold() == 'null':
            return output_dict
        else:
            output_dict[field] = self.convert_datetime(output_dict[field], input_format, output_format)

        return output_dict

    def clean_up(self):
        os.rename(self.working_dir + self.temp_filename, self.working_dir + self.file_name)

    def format_datetime(self, field, input_format, output_format):
        """
        API method for formatting a date field provided by the field parameter
        :param field: collumn to be formatted
        :param input_format: current state of the field
        :param output_format: desired state of the field
        """
        reader = self.initialize_reader()
        writer = self.initialize_writer()

        # Skip the header in the read file if we have one
        if self.has_header:
            next(reader)

        # Write the header
        writer.writeheader()

        for row in reader:
            writer.writerow(self.process_date_field(field, row, input_format, output_format))

        self.clean_up()

    @staticmethod
    def filter_row(input_dict, field, values):
        if input_dict[field] in values:
            input_dict = None

        return input_dict

    def filter_values(self, field, values):
        if not isinstance(values, list) and not isinstance(values, tuple):
            raise TypeError('Value for "values" parameter could not be handled. Must be of type list or tuple.')

        reader = self.initialize_reader()
        writer = self.initialize_writer()

        for row in reader:
            new_row = self.filter_row(row, field, values)
            if new_row:
                writer.writerow(new_row)

        self.clean_up()


    # TODO: See if we can abstract out to a "Apply Formatters" Method
