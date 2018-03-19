## How to contribute to Promgen

First of all, thank you so much for taking your time to contribute! We always welcome your ideas and feedback. Please feel free to make any pull requests.

* File an issue in [the issue tracker](https://github.com/line/promgen/issues) to report bugs and propose new features and improvements.
* Ask a question using [the issue tracker](https://github.com/line/promgen/issues).
* Contribute your work by sending [a pull request](https://github.com/line/promgen/pulls).

### Setting up Promgen for development

You can install Promgen for a development environment as follows.

```bash
python3 -m venv /path/to/virtualenv
source /path/to/virtualenv/bin/activate
pip install -e .[dev]
pip install mysqlclient # psycopg or another database driver
# Boostrap initial configuration
promgen bootstrap
# Enable DEBUG (and development) mode
echo 1 > ~/.config/promgen/DEBUG

# Amend bootstrapped configuration by hand: ~/.config/promgen/promgen.yml

# Setup or update database schemas, create initial user and shard
promgen migrate
# Run tests
promgen test
# Run development server
promgen runserver
```

By default promgen listens on port `8000`. Login with the user `admin` and password `admin`.
Remember to change the password!

> Note: Promgen strives to be a standard Django application. Make sure to apply standard Django development patterns.

#### Custom Configuration Directory

By default `promgen` uses `~/.config/promgen` as its configuration directory.
This can be changed by setting the environment variable `PROMGEN_CONFIG_DIR` to an alternative location whenever calling `promgen ...` commands.

### Contributor license agreement

If you are sending a pull request and it's a non-trivial change beyond fixing typos, please make sure to sign [the ICLA(individual contributor license agreement)](https://feedback.line.me/enquete/public/1719-k6U3vfJ4). Please contact us if you need the CCLA (corporate contributor license agreement).

### Code of conduct

We expect contributors to follow [our code of conduct](https://github.com/line/promgen/blob/master/CODE_OF_CONDUCT.md).
