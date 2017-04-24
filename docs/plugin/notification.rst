Notification Plugin
===================

Developing a Sender Plugin
--------------------------

Promgen uses sender plugins to route notifications to different services such as
Email or LINE Notify. Sender plugins are registered using setuptools entry_points_.

.. code-block:: python

    entry_points={
        'promgen.sender': [
            'sender_name = module.path.sender:SenderExample',
        ],
    }


Plugins should inherit from SenderBase, and at a minimum impelement a *_send()*
method

.. code-block:: python

    from promgen.celery import app as celery
    from promgen.sender import SenderBase

    class SenderExample(SenderBase):
        @celery.task(bind=True)
        def _send(task, target, alert, data):
            ## Code specific to sender
            print(target)
            print(alert)
            return True


Notes about Celery
------------------

Because of the way Celery works, when you wrap a method call with
```@celery.task```, you lose access to the self instance of the Sender class.
If you use ```@celery.task(bind=True)``` then you can get an instance of the
task. If you need to have an instance of the class, you can use this to get an
instance of the class

.. code-block:: python

    from promgen.celery import app as celery
    from promgen.sender import SenderBase

    class SenderCeleryExample(SenderBase):
        @celery.task(bind=True)
        def _send(task, target, alert, data):
            self = task.__klass__()
            ## Code specific to sender
            print(target)
            print(alert)
            return True
    # Set an instance we can retrive from within our _send method
    SenderCeleryExample._send.__klass__ = SenderCeleryExample


.. _entry_points: http://setuptools.readthedocs.io/en/latest/setuptools.html#automatic-script-creation
