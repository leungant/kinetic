import tempfile
import os

def test_log():
    kinetic_dir = tempfile.TemporaryDirectory()
    print(kinetic_dir.name)
    print(dir(kinetic_dir))
    print(f'kineticdev run --kinetic_dir={kinetic_dir.name}')
    os.system(f'kineticdev run --kinetic_dir={kinetic_dir.name}')

if __name__ == '__main__':
    test_log()
