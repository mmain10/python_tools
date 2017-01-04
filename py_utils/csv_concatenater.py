#!/usr/bin/python
import csv
import os
import sys



class CSVConcatenater:

    @staticmethod
    def get_csv_files_list(dir):
        """
        Returns a list of csv files from the absolute directory
        :param dir: absolute path to the directory of csvs
        :return: list of csv files
        """
        return [dir + file for file in os.listdir(dir) if file.endswith('.csv')]

    @staticmethod
    def generate_input_file_contents(input_csv):
        """
        Creates a generator stream from the input_csv
        :param input_csv:
        :return: generator stream
        """
        with open(input_csv) as stream:
            reader = csv.reader(stream)
            yield reader.next()

    @staticmethod
    def append_generator_stream(writer, generator):
        """
        Appends
        :param writer: a csv_writer instance
        :param generator: generator file stream
        """
        for row in generator:
            writer.writerow(row)

    def instantiate_writer(self, output_file):
        """
        Instantiates a csv.writer instance inside a context manager so we close up the file after we're done.
        :param output_file:
        :return:
        """
        with open(output_file, 'a') as unified_filename:
            csv_writer = csv.writer(unified_filename)
            return csv_writer

    def unify_files(self, file_list, output_filename):
        """
        Unifies the files streamed from file_list into output_file
        :param file_list: list of files for unification
        :param: name of the file created by unifying file_list
        :return: Nothing
        """
        csv_writer = self.instantiate_writer(output_filename)
        for file in file_list:
            generator_stream = self.generate_input_file_contents(file)
            self.append_generator_stream(csv_writer, generator_stream)

    def main(self, input_directory, output_filename):
        """
        Main algorithm for the process
        It first collects all of the .csv files in a folder (which are assumed to be the ones of interest)
        Then, it combines them all into a new file in the same directory as the others.
        The other files are kept around in case you wanted them.
        :param: input_directory: directory where files to be unified are found
        :param: output_filename: filename for the unified csv
        """
        file_list = self.get_csv_files_list(input_directory)
        self.unify_files(file_list, output_filename)


if __name__ == '__main__':
    directory = sys.argv[0]
    output_file = sys.argv[1]

    CSVConcatenater.main(directory, output_file)