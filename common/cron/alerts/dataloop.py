
import pymysql

from bi.cron.alerts.base import AlertSystem


class DataLoopAlertSystem(AlertSystem):

    def __init__(self, env_name, config_data):
        super().__init__(env_name, config_data)

        # Receive pymysql connection from underlying bi.cron.base.CronBase class instance.
        self.config = config_data
        self.tablename = config_data['tablename']

        self.status_codes = dict()
        self.status_codes['SUCCESS'] = 0
        self.status_codes['WARNING'] = 1
        self.status_codes['FAILURE'] = 2

    def connect_to_database(self):
        """Duplicate logic from CronBase."""

        original_config = self.config

        db_config = dict()
        db_config['host'] = original_config['host']
        db_config['user'] = original_config['user']
        db_config['db'] = original_config['db']
        db_config['password'] = original_config['password']
        db_config['charset'] = 'utf8mb4'
        db_config['cursorclass'] = pymysql.cursors.DictCursor

        self.db = pymysql.connect(**db_config)

    # NOTE: DO NOT DEFINE YOU OWN send_alert. You will lose the filtration implemented in AlertSystem.send_alert.

    # NOTE: This function ASSUMES that additional_data will be a string or string-compatible.
    def send_alert_internal(self, klass, level, title, additional_data):

        query = """
            INSERT
                INTO {}
                    ( source, err_date, status, err_msg, err_additional, env )
                VALUES
                    ( %s, NOW(), %s, %s, %s, %s )
            ;
        """.format(self.tablename)

        attributes = (klass, self.status_codes[level], title, additional_data, self.env_name)

        # print("Query: {}".format(query))
        # print("Attributes: {}".format(json.dumps(attributes)))

        # Connect RIGHT before sending alerts.
        # Otherwise this connection can timeout for long running processes.
        self.connect_to_database()

        with self.db.cursor() as cursor:
            result = cursor.execute(query, attributes)
            self.db.commit()
            return result
