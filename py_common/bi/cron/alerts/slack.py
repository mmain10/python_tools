
import json
import requests

from bi.cron.alerts.base import AlertSystem
from bi.cron.exception import CronException


class SlackAlertSystem(AlertSystem):

    def __init__(self, env_name, config_data):
        super().__init__(env_name, config_data)

        # NOTE: With Slack, do not default to sending ALL events, just significant ones (warnings and/or failures)
        self.set_monitored_levels(['WARNING', 'FAILURE'])

        self.endpoint = config_data['endpoint']
        self.username = config_data['username']

        self.colors = dict()
        self.colors['SUCCESS'] = 'good'
        self.colors['WARNING'] = 'warning'
        self.colors['FAILURE'] = 'danger'

    @staticmethod
    def append_field(field_collection, field_name, field_value):
        field = dict()
        field['title'] = field_name
        field['value'] = field_value
        field['short'] = True
        field_collection.append(field)

    # NOTE: DO NOT DEFINE YOU OWN send_alert. You will lose the filtration implemented in AlertSystem.send_alert.

    # NOTE: This function ASSUMES that additional_data will be a string containing JSON formatted data.
    def send_alert_internal(self, klass, level, title, raw_additional_data):

        msg = dict()
        msg['author_name'] = self.username
        msg['title'] = "{}: {}".format(level, title)
        msg['color'] = self.colors[level]

        fields = list()
        self.append_field(fields, 'source', klass)
        self.append_field(fields, 'level', level)
        self.append_field(fields, 'env', self.env_name)

        if raw_additional_data:

            additional_data = json.loads(raw_additional_data)

            if additional_data:
                for key in additional_data.keys():
                    if key != 'traceback':
                        self.append_field(fields, key, additional_data[key])

                preformatted = "\n".join(additional_data['traceback'])
                msg['text'] = "```{}```".format(preformatted)
                msg['mrkdwn_in'] = ['text']

        msg['fields'] = fields

        wrapper = dict()
        wrapper['username'] = self.username
        wrapper['attachments'] = [msg]

        result = requests.post(self.endpoint, json=wrapper)
        if result.status_code != 200:
            raise CronException('Failure sending Slack Alert.')
