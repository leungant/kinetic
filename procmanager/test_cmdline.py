import tempfile
import os

def test_log():
    kine_dir = tempfile.TemporaryDirectory()
    print(kine_dir.name)
    print(dir(kine_dir))
    print(f'kinedev run --kine_dir={kine_dir.name}')
    os.system(f'kinedev run --kine_dir={kine_dir.name}')

if __name__ == '__main__':
    test_log()
