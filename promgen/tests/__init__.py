import json
import os

with open(os.path.join(os.path.dirname(__file__), 'alertmanager.json')) as fp:
    TEST_ALERT = json.load(fp)

TEST_SETTINGS = {
    'promgen.sender.ikasan': {
        'server': 'http://ikasan.example',
    },
    'promgen.sender.linenotify': {
        'server': 'https://notify.example'
    }
}
