# Writing a sender plugin

## Add plugin to setup.py

```python
entry_points={
    'promgen.sender': [
        'sender_name = module.path.sender:SenderExample',
    ],
}
```

```python
from promgen.celery import app as celery
from promgen.sender import SenderBase

class SenderExample(SenderBase):
    @celery.task(bind=True)
    def _send(task, target, alert, data):
        ## Code specific to sender
        print(target)
        print(alert)
        return True
```

### Notes about Celery

Because of the way Celery works, when you wrap a method call with
```@celery.task```, you lose access to the self instance of the Sender class.
If you use ```@celery.task(bind=True)``` then you can get an instance of the
task. If you need to have an instance of the class, you can use this to get an
instance of the class

```python
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
```
