
"""Base functionality for Cron job classes. See CronBase class."""
import base64
import hashlib
import hmac
import os
import platform
import subprocess
import sys
import tempfile
import time
import traceback
import logging
import urllib.parse

import yaml

import jinja2
import json
import pymysql
import requests

from bi.cron.exception import CronException
from bi.cron.alerts.dataloop import DataLoopAlertSystem
from bi.cron.alerts.slack import SlackAlertSystem

LOG_FORMAT = "%(asctime)-15s %(name)s [%(levelname)-8s] -> %(message)s"
logging.basicConfig(format=LOG_FORMAT)


class CronBase(object):

    """Base functionality used by cron jobs"""

    def __init__(self, env_name, config_dir, data_file_dir, connection_names=[]):
        """
        :env_name: The environment ( from the configuration file ) to pass along.
        :config_dir: where to find our config.yaml file.
        :data_file_dir: where to find & create data files during process.
        :connection_names: list of names from provided configuration data to initialize connections to.
        """

        self.env_name = env_name
        self.data_file_dir = data_file_dir

        # Handle config load #####################################

        self.config_dir = config_dir
        self.config_filepath = self.config_dir + "/config.yaml"

        with open(self.config_filepath, "rb") as config_file:
            config = yaml.load(config_file)
            if self.env_name not in config:
                raise CronException("Environment Name: ({0}) not found in configuration.".format(self.env_name))
            self.config = config[self.env_name]
            self.config['env_name'] = self.env_name

        self.debug = (self.config['debug'] is True)

        # Setup Logger ###########################################

        self.logger = logging.getLogger(self.__class__.__name__)

        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        # DB connections #########################################

        self.connections = dict()

        for connection_name in connection_names:
            self.connect_to_database(connection_name)

        # Alerts #################################################
        self.alert_systems = dict()
        self.setup_bi_alerts()
        self.setup_slack_alerts()

    def set_debug(self, debug):
        """Setter for debug value AFTER initialization. To facilitate testing."""
        self.debug = debug

    # DATABASE FUNCTIONALITY ###########################################################################################

    def connect_to_database(self, database_name):
        """Configure connection to specific named database with config loaded from config file."""

        original_config = self.config['mysql'][database_name]

        db_config = dict()
        db_config['host'] = original_config['host']
        db_config['user'] = original_config['user']
        db_config['db'] = original_config['db']
        db_config['password'] = original_config['password']
        db_config['charset'] = 'utf8mb4'
        db_config['cursorclass'] = pymysql.cursors.DictCursor

        new_connection = pymysql.connect(**db_config)

        self.connections[database_name] = new_connection
        return new_connection

    def close_db_connection(self, database_name):
        """Wrapper for database connection termination against specific connection."""

        self.connections[database_name].close()
        del self.connections[database_name]

    def db_create_cursor(self, database_name):
        """Wrapper for database cursor instantiation against specific connection."""

        cursor = self.connections[database_name].cursor()
        return cursor

    def db_execute(self, database_name, statement, params):
        """Run statement(s) against configured database."""
        with self.db_create_cursor(database_name) as cursor:
            if self.debug:
                self.logger.debug("Running statement: " + statement)
            return cursor.execute(statement, params)

    def db_query(self, database_name, query, params):
        """Run query against configured database. FetchAll result"""

        with self.db_create_cursor(database_name) as cursor:
            if self.debug:
                self.logger.debug("Running Query: " + query)

            cursor.execute(query, params)
            return cursor.fetchall()

    # SUBPROCESS FUNCTIONALITY #########################################################################################

    def run_subprocess(self, *cmd_and_args):
        """ Wrap the process of creating a subprocess. Captures output in debug mode. """

        command_line = " ".join(cmd_and_args)
        self.logger.debug("Running: %s", command_line)

        return subprocess.Popen(command_line, shell=True, close_fds=True)

    def ensure_process_results(self, process_object, label):
        """ Check for a successful exit code for the provided process object.
            Returns a copy of stdout/stderr in debug mode. """
        self.logger.debug("Waiting for %s to complete.", label)
        process_object.wait()

        self.logger.debug("%s completed with return code: %d.", label, process_object.returncode)

        if process_object.returncode != 0:
            # This is an error condition.
            raise CronException("Process did not finish with a non-error (0) return code.")

    # FILESYSTEM FUNCTIONALITY #########################################################################################

    @staticmethod
    def ensure_file_exists(file_path):
        """ Check for the existance of the provided file_path """

        if not (os.path.exists(file_path) and os.access(file_path, os.R_OK)):
            # This is bad.
            raise CronException("Path {0} does not exist or can not be read.".format(file_path))

    @staticmethod
    def ensure_symlink_exists(symlink_path, file_path):
        """ Check for the existance of the provided symlink path """

        if not (os.path.islink(symlink_path) or (os.path.realpath(symlink_path) != os.path.realpath(file_path))):
            # This is bad.
            raise CronException("Path {0} is not a symlink or does not point where expected.".format(symlink_path))

    # ALERT FUNCTIONALITY ##############################################################################################

    def set_alert_levels(self, alert_system, monitored_levels):
        """Change the monitored event levels for a named alert system (If one has been registered)."""
        if alert_system in self.alert_systems.keys():
            self.alert_systems[alert_system].set_monitored_levels(monitored_levels)

    def setup_bi_alerts(self):
        """Add the DataloopAlertSystem into our alerts configurations for automatic state reporting."""
        if 'bi_alerts' in self.config['mysql'].keys():
            self.add_alert_system('bi_alerts', DataLoopAlertSystem(self.env_name, self.config['mysql']['bi_alerts']))
        else:
            self.logger.warn('No configuration found for DataLoopAlertSystem')

    def setup_slack_alerts(self):
        """Add the SlackAlertSystem into our alerts configurations for automatic state reporting."""
        if 'slack' in self.config.keys():
            self.add_alert_system('slack', SlackAlertSystem(self.env_name, self.config['slack']))
        else:
            self.logger.warn('No configuration found for SlackAlertSystem')

    @staticmethod
    def build_descriptive():
        return "CronBase processing"

    @staticmethod
    def build_error_output():
        """Build a well formatted string based on the provided exception information."""

        error_type, error_value, error_tb = sys.exc_info()

        alert_data = dict()
        alert_data['type'] = type(error_value).__name__
        alert_data['value'] = str(error_value)
        alert_data['host'] = platform.node()
        alert_data['os'] = platform.system()
        alert_data['traceback'] = traceback.format_list(traceback.extract_tb(error_tb))

        return alert_data

    def add_alert_system(self, system_name, alert_obj):
        """Adding an alert system into the collection
           so that each noted system will receive all given alerts."""

        self.alert_systems[system_name] = alert_obj

    def send_alert(self, level, title, additional_data):
        """Ingest and provide the supplied alert details to each of the registered alert systems."""

        full_title = "{}: {}".format(self.build_descriptive(), title)

        # Make sure that additional_data is a string ... OR, make it JSON.
        if not isinstance(additional_data, str):
            additional_data = json.dumps(additional_data)

        self.logger.debug("Sending Alert -> {} :: {} :: {}".format(level, full_title, additional_data))

        # Send the alert to each of the systems, The alert system(s) will be responsible for filtering.
        for system in self.alert_systems.values():
            system.send_alert(self.__class__.__name__, level, full_title, additional_data)

    # Template Processing via Jinja ####################################################################################

    def load_template(self, template_name):
        template_config = self.config["templates"]
        template_file_path = os.path.abspath("{}{}{}".format(template_config["path"],
                                                    template_name,
                                                    template_config["extension"]))

        with open(template_file_path) as template_file:
            return jinja2.Template(template_file.read())

    def render_template(self, template_name, data):
        return self.load_template(template_name).render(**data)

    # EMAIL via Mozmail ################################################################################################

    @staticmethod
    def build_email_signature(string, secret, urlencode=True):
        string = bytes(string, 'utf-8')
        secret = bytes(secret, 'ascii')
        signature = hmac.new(secret, string, hashlib.sha1).digest()
        signature = base64.b64encode(signature)
        if urlencode:
            signature = urllib.parse.quote_plus(signature)
        return signature

    def build_email_content(self, **kwargs):

        mozmail_config = self.config['mozmail']

        required_args = ['to', 'subject']
        for arg in required_args:
            if arg not in kwargs:
                raise ValueError("'{}' expected but not provided in arguments.".format(arg))

        has_body = False
        if 'text_body' in kwargs:
            has_body = True
        if 'html_body' in kwargs:
            has_body = True

        if not has_body:
            raise ValueError("'text_body' or 'html_body' expected but neither provided in arguments.")

        content = dict(kwargs)
        content['user_id'] = mozmail_config['from_user_id']
        content["to_address"] = kwargs['to']
        content["subject"] = kwargs['subject']
        content["type"] = mozmail_config['email_type']

        if 'text_body' in kwargs:
            content["plaintext"] = kwargs['text_body']

        if 'html_body' in kwargs:
            content["html"] = kwargs['html_body']

        return content

    def send_email(self, **kwargs):

        mozmail_config = self.config['mozmail']

        email_content = self.build_email_content(**kwargs)

        payload = dict()
        payload['messages'] = [email_content]
        payload['access_id'] = mozmail_config['access_id']
        payload['expires'] = time.time()

        payload_json = json.dumps(payload)
        self.logger.debug("Email Payload: {}".format(payload_json))
        signature = self.build_email_signature(payload_json, mozmail_config['secret'])

        request_headers = dict()
        request_headers['X-Mozmail'] = signature
        request_headers['Content-Type'] = 'application/json'
        request_headers['Accept'] = 'application/json'

        response = requests.post(mozmail_config["endpoint"], json=payload, headers=request_headers)
        parsed_response = response.json()

        if 'messages' in parsed_response:
            messages = parsed_response['messages']
            if messages[0] != 'ok':
                raise CronException("Unable to send email: {}".format(messages[0]))

        return parsed_response

    # HTTP #############################################################################################################

    def setup_requests_debugging(self):
        """Wrap up the logic to cause requests to provide deep debug logging of input & output."""

        # These two lines enable debugging at httplib level (requests->urllib3->http.client)
        # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
        # The only thing missing will be the response.body which is not logged.
        try:
            import http.client as http_client
        except ImportError:
            # Python 2
            import httplib as http_client
        http_client.HTTPConnection.debuglevel = 1

        # You must initialize logging, otherwise you'll not see debug output.
        self.logger.setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    def http_request(self, url, method, accept_type, body, content_type, to_file=None):
        """
        :param url: The endpoint URL to communicate with.
        :param method: The method 'get', 'post', etc.
        :param accept_type: The content-type expected, usually 'application/json'
        :param body: The body content to send in the request.
        :param content_type: The content-type being sent.
        :param to_file: A filepath to write the response content to.
        :return: The content as decoded json unless to_file is provided, then the length of the content written.
        """

        if self.debug:
            self.setup_requests_debugging()

        request_headers = dict()
        request_headers['Accept'] = accept_type

        if content_type:
            request_headers['Content-Type'] = content_type

        self.logger.debug("Sending request to %s", url)
        self.logger.debug(body)

        request_method = getattr(requests, method)
        response = request_method(url,
                                  data=body,
                                  headers=request_headers,
                                  auth=(self.username, self.password))

        if to_file:
            with open(to_file, 'wb') as output_file:
                output_file.write(response.content)
            return len(response.content)
        else:
            response_content = response.json()
            return response_content


    # RUNTIME FUNCTIONALITY ############################################################################################

    def run(self):
        """This method should NOT be overridden.
           Child classes should implement cron_process which is the meat of the process."""

        try:
            self.send_alert('SUCCESS', "Job START", None)
            self.cron_process()
            self.send_alert('SUCCESS', "Job FINAL", None)
            sys.exit(0)

        except Exception:
            alert_data = self.build_error_output()
            self.send_alert('FAILURE', 'Failure during Job', alert_data)
            sys.exit(1)

    def cron_process(self):
        """ Run the processes & collect the results """
        raise CronException("Base {} method called. Must be overriden.".format(self.__class__))
