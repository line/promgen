## How to contribute to Promgen

First of all, thank you so much for taking your time to contribute! We always welcome your ideas and feedback. Please feel free to make any pull requests.

- File an issue in [the issue tracker](https://github.com/line/promgen/issues) to report bugs and propose new features and improvements.
- Ask a question using [the issue tracker](https://github.com/line/promgen/issues).
- Contribute your work by sending [a pull request](https://github.com/line/promgen/pulls).

### Setting up Promgen for development

The Promgen repository has a Makefile with various commands to make development easier.
You can see some of the commands by running `make help`

```bash
# If you need to install Python first, try using your system's package manager
# Examples
# yum install python3 python3-pip
# homebrew install python3
# If using OSX with Homebrew, you may need to export some flags
# to get mysql client to install
# export LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib"
make bootstrap
# If you want to enable DEBUG (and development mode)
echo 1 > ~/.config/promgen/DEBUG

# Amend bootstrapped configuration by hand: ~/.config/promgen/promgen.yml

# Setup or update database schemas, create initial user and shard
make migrate
# Run tests
make test
# Run development server
make runserver
```

By default promgen listens on port `8000`. Login with the user `admin` and password `admin`.
Remember to change the password!

> Note: Promgen strives to be a standard Django application. Make sure to apply standard Django development patterns.

#### Custom Configuration Directory

By default `promgen` uses `~/.config/promgen` as its configuration directory.
This can be changed by setting the environment variable `PROMGEN_CONFIG_DIR` to an alternative location whenever calling `promgen ...` commands.

### Contributor license agreement

When you are sending a pull request and it's a non-trivial change beyond fixing typos, please sign
[the ICLA (individual contributor license agreement)](https://cla-assistant.io/line/promgen).
Please [contact us](mailto:dl_oss_dev@linecorp.com) if you need the CCLA (corporate contributor license agreement).

### Code of conduct

We expect contributors to follow [our code of conduct](https://github.com/line/promgen/blob/master/CODE_OF_CONDUCT.md).
