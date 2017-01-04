#BI Common Cron Base and Alerts ( for Python )

The py_common module is used to collect code that can be implemented in several situations and could be useful to supplement a variety of projects.

##Using CronBase
###Importing
While creating a project in the `BI_Automation` repository, it's important to add the py_common module to your `sys.path`. 
The code snippet below should be included as part of your imports if you intend to implement the CronBase class:
```python
sys.path.append(os.path.abspath('../py_common/'))
from bi.cron.base import CronBase
from bi.cron.exception import CronException
```

From the snippet above, you can either deploy your project near the `py_common` directory, so that the above path describes
where to look for the `bi.cron` module, or you can alter the relative path appended to the syspath.

###Extending
In python 3, extending a new class as a child of CronBase is as simple as saying `class MyNewCronClass(CronBase):`. Now 
you have all of the methods from CronBase inherited by your new class.

###Free Functionalities and Benefits
By extending your new class from CronBase, you get a host of helpful methods for free. A small list is compiled below:

1. *Multiple Database Connection layers*
   _You can reference connections easily and quickly as an attribute of the class and querying the database becomes very
    simple with the_ `db_query` _method_
2. Run a subprocess:
   _This allows you to run a process as if via the commandline, ensure its results, and store the output_
3. Send email via Mozmail

4. Send HTTP Requests:
  _Specifying the method, auth, headers, and payload are done via the_ `http_request` _method_
5. Send Dataloop Alerts via Slack or Email
  _These alerts come pre-cooked and ready to go right out of the box--the main advantage for extending this class_

####Configuring Database Connections
When specifying connections passed to the `CronBase` parent class, the class will attempt to instantiate the connection 
using the `connection_name` listed under the `mysql` portion of the config file, which matches the `connection_name`
passed to it. If `connection_name` is not an element under `mysql`, the object will throw an exception and fail to connect.
The credential elements (i.e. `host`, `username`, `password`) should be children of the `connection_name` key.

Example:

In `config.yaml`
```yaml
  mysql:
    bi_alerts:
      user: *std_user
      password: *std_pass
      db: some_db
      host: *std_host
      tablename: alerts_tablename
    your_connection:
      user: your_username
      password: your_pass
      db: some_db
      host: your_connection_host
```

In object extending `CronBase`:

```python
class MyObject(CronBase):

    def __init__(self, **your_class_args)
        .
        .
        .
        super().__init__(env_name, config_dir, data_file_dir, connections=['your_connection']) # this works!
        .
        .
        .
        super().__init__(env_name, config_dir, data_file_dir, connections=['my_connection'])  # this will fail because of naming mismatch.
        .
        .
        .
```

####Configuring Alerts
In order to begin configuration for alerts, you'll need to provide the configuration details for each respective piece. 
Slack's configuration details fall directly under the `slack` element key in the configuration file. Our Dataloop alerts
 however, require database configuration, which fits under the `mysql` element, the connection must be called `bi_alerts`
 and contain typical connection information (for details you can look at the `example_configuration.yaml`).
Addtionally, you can specify the alert levels which get sent to each configured channel. Using the `set_alert_levels`, 
its possible to specify the alert events which get sent to a particular channel. 
`self.set_alert_levels('slack', ['SUCCESS', 'WARNING', 'FAILURE'])` would show all event types on the slack alert channel.

###Configuration
The `CronBase` class only requires 3 arguments at construction:
1. env_name - name of the top level key in your configuration file. This allows you to define many different 
environment configurations within the same `config.yaml` file, such as `prod`, and `staging`, or any additional environment types you wish
to define.
2. config_dir - directory containing the configuration file named `config.yaml`
3. data_file_dir - a directory for storing, creating, and reading data files necessary to your process.

An example config to a real process can be found [here](https://github.com/seomoz/BI_Automation/blob/master/projects/zuora_export/config/config_example.yaml)
A bare-bones requirements example for the `CronBase` is in the `example_configuration.yaml` file located in this directory.

Thus constructing a minimal instance of `CronBase` would look something like: 
`instance = ObjectExtendingCronBase('prod', './config_dir', './data_files', **other_args)`

###Overriding `cron_process` and other methods
In order to properly run with all of the alerts, emails, and free functionality provided by CronBase, the main algorithm
 of your project needs to override the `cron_process` method. 
Additionally, to build the error output in a format you like, its recommended that you override the `build_descriptive` 
method; this may not be necessary for you, but will help your end users decipher the source of the Alerts.
After implementing your overridden `cron_process` method, you're ready to get started.

###Executing the Process
When looking to actually execute your code, you will call the `run` method which you inheritted from `CronBase`. This method takes care of exception handling, and sends alerts out automagically as long as you overrode `cron_process`.
Example:
```python
class MyCronJobObject(CronBase):
   .
   .
   .
   .
   
   def cron_process(self, *args):
      # ... (Define your process in here) ...
   

if __name__ == '__main__':
    MyCronJobObject(env_name, config_directory, data_file_dir).run()
```
