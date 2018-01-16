## How to contribute to Promgen

First of all, thank you so much for taking your time to contribute! We always welcome your ideas and feedback. Please feel free to make any pull requests.

* File an issue in [the issue tracker](https://github.com/line/promgen/issues) to report bugs and propose new features and improvements.
* Ask a question using [the issue tracker](https://github.com/line/promgen/issues).
* Contribute your work by sending [a pull request](https://github.com/line/promgen/pulls).

### Setting up Promgen for development

You can install Promgen for a development environment as follows.

```bash
virtualenv --python=/path/to/python3 /path/to/virtualenv
source /path/to/virtualenv/activate
pip install -e .[dev]
pip install mysqlclient # psycopg or another database driver
# Setup database and update tables
promgen migrate
# Run tests
promgen test
# Run development server
promgen runserver
```

> Note: Promgen strives to be a standard Django application. Make sure to apply standard Django development patterns.

### Contributor license agreement

If you are sending a pull request and it's a non-trivial change beyond fixing typos, please make sure to sign [the ICLA(individual contributor license agreement)](https://feedback.line.me/enquete/public/1719-k6U3vfJ4). Please contact us if you need the CCLA (corporate contributor license agreement).

### Code of conduct

We expect contributors to follow [our code of conduct](https://github.com/line/promgen/blob/master/CODE_OF_CONDUCT.md).
