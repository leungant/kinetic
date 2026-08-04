from procmanager.db import *
from procmanager import db

def test_db1():
    db.filename = 'test.db'


    db._clear_db()
    create_db()
    insert_job_instance('hasdf id', 'hello')
    list_job_instances()
