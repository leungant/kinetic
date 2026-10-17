import os
import tempfile
import requests

from procmanager.config import HOME_BIN
from procmanager.config import KINETIC_BINARY_URL_X64


# path = ~/.config/systemd/user/kinetic.service
kinetic_dot_service_file= """
[Unit]
Description=A process runner

[Service]
Type=simple
ExecStart=%h/bin/kinetic serve
PrivateTmp=true
Restart=Always

[Install]
# WantedBy=default.target
WantedBy=multi-user.target
"""


def install_systemd():
    systemctl_path = os.path.expanduser('~/.config/systemd/user/')
    os.makedirs(systemctl_path, exist_ok=True)
    with open(f'{systemctl_path}/kinetic.service', 'w') as f:
        f.write(kinetic_dot_service_file)
    print('Enabling linger for systemctl...')
    os.system('loginctl enable-linger $(whoami)') 
    print('Reloading systemctl')
    os.system('systemctl --user daemon-reload')
    os.system('systemctl --user enable kinetic')
    os.system('systemctl --user restart kinetic')
    os.system('systemctl --user status kinetic')

def uninstall_systemd():
    import platform
    if platform.system() != 'Linux':
        return
    os.system('systemctl --user disable kinetic')
    systemctl_path = os.path.expanduser('~/.config/systemd/user/')
    os.system(f'rm {systemctl_path}/kinetic.service')


KINETIC_CRON_COMMAND = '@reboot  sleep 5; ~/bin/kinetic start  # KINETIC_CRON_LINE'

def _update_cron(new_cron_text):
    with tempfile.NamedTemporaryFile() as f:
        f.write(new_cron_text.encode())
        f.seek(0)
        print("new cron:")
        print(open(f.name).read())
        f.seek(0)
        cron_install_output = os.popen(f"crontab {f.name}").read()
        print(cron_install_output)

def install_cron():
    crontext = os.popen("crontab -l").read()
    if crontext:
       print("crontext" + crontext)
       cronlines = crontext.split("\n") 
       cron_stripped_lines = [line.strip() for line in cronlines]
       print("cron_stripped_lines ")
       print( cron_stripped_lines)
       if KINETIC_CRON_COMMAND in cron_stripped_lines:
           return
    new_cron_text = crontext
    new_cron_text += "\n"
    new_cron_text += KINETIC_CRON_COMMAND
    new_cron_text += "\n"
    print("new_cron_text" + new_cron_text)
    _update_cron(new_cron_text)


def uninstall_cron():
    crontext = os.popen("crontab -l").read()
    if crontext:
       print("crontext" + crontext)
       cronlines = crontext.split("\n") 
       # new_cron_lines = [line for line in cronlines if line.strip() != KINETIC_CRON_COMMAND]
       new_cron_lines = [line for line in cronlines if 'KINETIC_CRON_LINE' not in line]
       new_cron_text = "\n".join(new_cron_lines)
       if new_cron_text:
           new_cron_text += '\n'
       _update_cron(new_cron_text)
       if 'kinetic' in new_cron_text:
           print('A manual kinetic line may still be in your crontab')


def do_update():
    # 1 dl relevant binary from gh
    save_path = os.path.expanduser('~/bin')
    os.makedirs(save_path, exist_ok=True)
    
    # 2 copy to ~/bin/kinetic
    bin_path = os.path.join(f'{HOME_BIN}', 'kinetic')
    url_path = KINETIC_BINARY_URL_X64
    print(f'Downloading from {url_path}')
    #with urllib.request.urlopen(KINETIC_BINARY_URL_X64) as response,\ needs headrs
    #  open(bin_path, 'wb') as f:
    #    shutil.copyfileobj(response, f)
    # subprocess.run(f'curl -O https://kinetic.icedb.info/x64/kinetic', cwd=save_path)


    r = requests.get(f'{KINETIC_BINARY_URL_X64}')
    #with open(bin_path, 'wb') as f:
    #    f.write(r.content)
    with tempfile.NamedTemporaryFile(delete=False) as fp:  # delete_on_close avail 3.12+
        fp.write(r.content)
    os.chmod(fp.name, 0o744)
    os.rename(fp.name, bin_path)

    # Refresh the service file and ensure it is running and refresh the binary for systemd.
    install()


if __name__ == '__main__':
    install_cron()
    #install()
