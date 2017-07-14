Auth Plugins
============

Promgen uses auth plugins based on `Django's auth backend`_ and the
`Python Social Auth`_. They are registered in Promgen's settings file

.. code-block:: yaml

    # Add keys and secrets to promgen.yml
    # Make sure you add Django's ModelBackend if you want to allow users to
    # login with a Django user
    django:
      AUTHENTICATION_BACKENDS:
      - module.path.auth.ExampleAuth
      - social_core.backends.github.GithubOAuth2
      - django.contrib.auth.backends.ModelBackend
      SOCIAL_AUTH_EXAMPLE_KEY: foo
      SOCIAL_AUTH_EXAMPLE_SECRET: bar
      SOCIAL_AUTH_GITHUB_KEY: a1b2c3d4
      SOCIAL_AUTH_GITHUB_SECRET: e5f6g7h8i9

.. _Python Social Auth: http://python-social-auth.readthedocs.io/en/latest/index.html

.. _Django's auth backend: https://docs.djangoproject.com/en/1.10/topics/auth/customizing/
