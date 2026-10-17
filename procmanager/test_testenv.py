import tempfile
import os

def test_env():
    td = tempfile.TemporaryDirectory()
    os.environ['KINETIC_TEST_PATH'] = td.name
    print(td.name)
    print(os.getenv('KINETIC_TEST_PATH'))
    print(os.environ['KINETIC_TEST_PATH'])

    from procmanager import config
    print(config.TEST_PATH)
    print(config.BASE_PATH)
    #print(dir(config))
    #print(config.BASE_PATH)
    '''for a in dir(config):
        try:
            print(a)
        except Exception as e:
            pass
'''

if __name__ == '__main__':
    test_env()
