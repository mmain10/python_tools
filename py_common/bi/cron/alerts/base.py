
class AlertSystem:
    def __init__(self, env_name, config_data, levels=['SUCCESS', 'WARNING', 'FAILURE']):
        self.config = config_data
        self.levels = levels
        self.monitored_levels = levels
        self.env_name = env_name

    def set_monitored_levels(self, new_levels):
        """Provide an updated list of levels that we want to track alerts for.
            This list is filtered through self.levels and only the intersection is kept."""

        self.monitored_levels = [level for level in new_levels if level in self.levels]

    def send_alert(self, klass, level, title, additional_data):
        """Base implementation for all alert systems.
            Ensure the requested level is supported by and watched before sending alert."""

        # Ensure the requested level is one we support.
        if level not in self.levels:
            return

        # Ensure the requested level is one we've been asked to watch for.
        if level not in self.monitored_levels:
            return

        # print("  -> Sending Alert via {}.".format(self.__class__.__name__))
        return self.send_alert_internal(klass, level, title, additional_data)
