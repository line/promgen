# What is Promgen?

Promgen is a configuration file generator for [Prometheus](http://prometheus.io). Promgen is a web application written in Ruby and can help you do the following jobs.

* Create and manage Prometheus configuration files
* Configure alert rules and notification options

See the [Promgen introduction slides](http://www.slideshare.net/tokuhirom/promgen-prometheus-managemnet-tool-simpleclientjava-hacks-prometheus-casual) for more details.

## Promgen screenshots


## Getting started

Promgen attemps to use the [XDG] spec and follow suggestions for [12factor] apps

```bash
# Create configuration directory
mkdir -p ~/.config/promgen
# For production deployment, you may need to create the cache directory
mkdir -p ~/.cache/promgen
# Set Database URL
echo 'mysql://promgen:promgen@localhost/pypromgen' > ~/.config/promgen/DATABASE_URL
# Generate Secret key
date | shasum > ~/.config/promgen/SECRET_KEY
# Turn on DEBUG mode for Django
touch ~/.config/promgen/DEBUG
# Copy and edit configuration file
cp promgen/tests/examples/settings.yaml ~/.config/promgen/settings.yaml
vim ~/.config/promgen/settings.yaml
```

[Example configuration file][Settings]

## Installing Promgen for Development

```bash
virtualenv --python=/path/to/python3 /path/to/virtualenv
source /path/to/virtualenv/activate
pip install -e .[dev]
pip install mysqlclient # psycopg or another database driver
# Setup database and update tables
promgen migrate
# Run development server
promgen runserver
```

## Configure Prometheus to read Promgen generated configurations

This is an example configuration for Prometheus.

```
rule_files:
- "/tmp/prom.rule"

scrape_configs:
  - job_name: 'dummy'
    file_sd_configs:
      - files:
        - "/tmp/prom.json"
```

When you add a host on the browser, Promgen automatically generates a /tmp/prom.json file. The information is then updated in a format as shown below.

```
[
  {
    "targets":[
      "blog.admin1.localhost:9100"
    ],
    "labels":{
      "service":"blog",
      "project":"blog-admin",
      "farm":"blog-admin-RELEASE",
      "job":"node"
    }
  },
  {
    "targets":[
      "blog.admin1.localhost:9113"
    ],
    "labels":{
      "service":"blog",
      "project":"blog-admin",
      "farm":"blog-admin-RELEASE",
      "job":"nginx"
    }
  }
]
```


[XDG]: https://specifications.freedesktop.org/basedir-spec/latest/ar01s03.html
[12factor]: https://12factor.net/
[Settings]: promgen/tests/examples/settings.yaml
