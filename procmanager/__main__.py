# Main entry point
import argparse
from datetime import datetime
import gzip
import os
import glob

from procmanager.job_instance import actually_run_job
from procmanager.config import load_job_defs, LOG_DIR, BASE_PATH, HOME_BIN
from procmanager.install import install_systemd, uninstall_systemd, do_update, install_cron, uninstall_cron 
from procmanager.server import stop_existing_server
import procmanager.db

def serve(args):
    from procmanager.server import start_server
    start_server(args=args) # must use named arguments

def run(args):
    if args.jobname:
        actually_run_job(args.jobname)
        #actually_run_job(args.jobname, args.transition_type, args.prev_job_id) # TODO TRANSITIONS
    else:
        args.sub_parser.print_help()

def show_help( args):
    args.parser.print_help()

def list_(args):
    import toml
    #print(load_job_defs())
    JOB_DEFS, JOB_DEF_ERRORS = load_job_defs()
    print(toml.dumps(JOB_DEFS))
    print(JOB_DEF_ERRORS)
    # TODO should really print the original files with comments here. maybe get people to put comments in a description/help/comments field


from colorama import just_fix_windows_console
just_fix_windows_console()
# There's also blessings for bold, underline.

def show_log_app(args):
    from procmanager.prompt_view import run_app
    run_app()

def show_log(args):
    from procmanager.tui_helpers import generate_log_table
    rows, properties = generate_log_table(last=1000) 
    import tabulate
    print(tabulate.tabulate(rows[-1000:]))
    return



def edit(args):
    # get editor
    # launch editor with solo file if only one file or allow user to choose a file.
    # or show all jobs and save the changes to the respective file.
    #from configparser import ConfigParser
    #cp = ConfigParser(allow_unnamed_section=True)
    # if linux
    
    config_files = glob.glob(f'{BASE_PATH}/job_defs/*')
    se_path = '~/.selected_editor'
    se_path = os.path.expanduser(se_path)
    if os.path.exists(se_path):
        with open(se_path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith('SELECTED_EDITOR='):
                editor = line.split('=')[1].strip()
                editor = editor[1:-1]  # '/usr/bin/nano'
                print(editor)
                print(config_files)
                os.system(f'echo {editor} {" ".join(config_files)}')
                os.system(f'{editor} {" ".join(config_files)}')


    # with NamedTemporaryFile
    # open example.toml
    # then save example.toml
    # then reload config in the scheduler
    # TODO
    jd, jd_errors = load_job_defs()
    print(jd)
    print(jd_errors)


#def reload(args):
#    # TODO
#    host, port = 'localhost', 8737
#    auth = None
#    requests.get(f'{host}:{port}/reload_config')

def print_job_log(args):
    job_log_path = f"{LOG_DIR}/{args.job_id}.log"
    open_fn = open
    open_mode = 'r'
    if not os.path.exists(job_log_path):
        job_log_path = job_log_path + '.gz'
        open_fn = gzip.open
        open_mode = 'rt'

    with open_fn(job_log_path, open_mode) as f:
        for line in f.readlines():
            print(line, end='')

    print(args.edit)

def start(args):
    """ create and start systemctl service or win service """
    install(args) 
    # TODO should return control, should run only one (whereas serve won't check). 
    # maybe serve should check, shouldn't keep output from child processes, but should
    # display output if run from command line
    serve(args)

def stop(args):
    """ stop systemctl service or win service """
    os.system("systemctl --user stop kine") 
    os.system("systemctl --user status kine") 
    """ stop crontab started service """
    stop_existing_server()


def install(args):
    install_cron()

def uninstall(args):
    """ remove crontab entry, service """
    uninstall_cron()
    uninstall_systemd()

def status(args):
    print('show status')
    # Server pid and up or not
    print(f'Server status: {procmanager.db.get_server_status()}')
    # job defs parsing status
    print(f'Job defs status: {procmanager.db.get_job_defs_status()}')
    # number of timers running?

def version(args):
    print(1.00)


def update_(args):
    """ Upgrade and copy binary to $HOME/bin - ought to be interactive"""
    maybe_yes = input("Are you sure you wish to update the kine binary (y or n + Enter) \n")
    if maybe_yes.lower() == 'y':
        do_update()







def main():
    """ quick primer on argparse:
          subparsers are subcommands in argparse. set_defaults sets the function to run.
         args.func(args) actually runs the command 
         """
    parser = argparse.ArgumentParser()
    # parser.add_argument("--jobname", type=str)
    
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='additional help')
    parser_serve = subparsers.add_parser('serve')
    parser_serve.set_defaults(func=serve)
    parser_serve.add_argument('--port', default=8737, type=int)

    parser_run = subparsers.add_parser('run')
    parser_run.set_defaults(func=run, sub_parser=parser_run)
    parser_run.add_argument('jobname')
    parser_run.add_argument('--transition-type', default=None, type=str)
    parser_run.add_argument('--prev-job-id', default=None, type=str)

    parser_help = subparsers.add_parser('help')
    parser_help.set_defaults(func=show_help, parser=parser)

    parser_list = subparsers.add_parser('list')
    parser_list.set_defaults(func=list_, sub_parser=parser_list)

    parser_edit = subparsers.add_parser('edit')
    parser_edit.set_defaults(func=edit, sub_parser=parser_edit)

    parser_log = subparsers.add_parser('log')
    parser_log.set_defaults(func=show_log, sub_parser=parser_log)
    parser_log = subparsers.add_parser('ll', help="log in live mode")
    parser_log.add_argument('follow', action='store_true', default=True)
    parser_log.set_defaults(func=show_log_app, sub_parser=parser_log)
    #parser_log = subparsers.add_parser('lll', help="log in live mode")
    #parser_log.add_argument('follow', action='store_true', default=True)
    #parser_log.set_defaults(func=show_log_app, sub_parser=parser_log)
    parser_print_job_log = subparsers.add_parser('jl', help="show/edit (cat/$EDITOR) output for job_id", aliases=['cat'])
    parser_print_job_log.add_argument('job_id', type=str)
    parser_print_job_log.add_argument('--edit', '-e', action='store_true', default=False)
    parser_print_job_log.set_defaults(func=print_job_log, sub_parser=parser_print_job_log)

    parser_start = subparsers.add_parser('start')
    parser_start.set_defaults(func=start, sub_parser=parser_start)

    parser_stop = subparsers.add_parser('stop')
    parser_stop.set_defaults(func=stop, sub_parser=parser_stop)
    
    parser_version = subparsers.add_parser('version')
    parser_version.set_defaults(func=version, sub_parser=parser_version)

    parser_update = subparsers.add_parser('update')
    parser_update.set_defaults(func=update_, sub_parser=parser_update)

    parser_install = subparsers.add_parser('install')
    parser_install.set_defaults(func=install, sub_parser=parser_install)

    parser_uninstall = subparsers.add_parser('uninstall')
    parser_uninstall.set_defaults(func=uninstall, sub_parser=parser_uninstall)

    parser_status = subparsers.add_parser('status')
    parser_status.set_defaults(func=status, sub_parser=parser_status)



    #foo_parser = subparsers.add_parser('foo')
    #parser.add_argument("--serve")
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)  
    else:
        parser.print_help()

    # if args.jobname:
    #     actually_run_job(args.jobname)
    # else:
    #     start_server()

if __name__ == "__main__":
    main()
