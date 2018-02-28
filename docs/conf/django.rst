Configuring Django
==================

Arbitrary `django <https://www.djangoproject.com/>`__ settings can be
set for the promgen web app by adding those under the ``django`` key to
the ``promgen.yml`` file.

All available django settings (not every setting may apply to promgen)
are listed in the `django
reference <https://docs.djangoproject.com/en/1.11/ref/settings/>`__.

Configuring an SMTP Server
--------------------------

An SMTP server for sending outgoing mail can be configured this way:

.. code-block:: yaml

    promgen.notification.email:
      sender: promgen@example.com

    django:
      EMAIL_HOST: mail.example.com
      EMAIL_PORT: 587
      EMAIL_HOST_USER: user@example.com
      EMAIL_HOST_PASSWORD: <secret password>
      EMAIL_USE_TLS: true

The ``EMAIL_USE_TLS`` and ``EMAIL_USE_SSL`` settings are mutually
exclusive. The ``EMAIL_USE_SSL`` setting enables implicit TLS, the
``EMAIL_USE_TLS`` setting enables STARTTLS.

The `django docs on
email <https://docs.djangoproject.com/en/1.11/topics/email/>`__ cover how
emails are sent by django as well as relevant configuration parameters.
