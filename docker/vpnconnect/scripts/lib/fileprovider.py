from string import Template
import subprocess, logging, argparse, os, pathlib, threading, socket, shutil
from contextlib import closing

class fileprovider:
    conf_template = """
[global]
    map to guest = Bad User
    log file = /var/log/samba/%m
    smb ports = $port
    security = user
    workgroup = $workgroup
    add user script = /usr/local/sbin/add_user_script %u
    #protocol = SMB2
    guest account = $guest
    host msdfs = no

[$share]
    path = $path
    read only = yes
    guest ok = yes
    valid users = $user
"""
    default_args = ["--foreground", "--no-process-group", "-d", "2", "--debug-stdout"]
    executable = '/usr/sbin/smbd'
    config_file = '/etc/samba/smb.conf'

    default_port = 445
    default_path = '/srv'
    default_share = 'deployment'
    default_workgroup = 'DEPLOYER'
    default_user_env = 'SMB_USERNAME'
    default_password_env = 'SMB_PASSWORD'
    default_user_system = os.getenv(default_user_env)
    default_password_system = os.getenv(default_password_env)
    default_username = default_user_system
    default_passwort = default_password_system

    def __init__(self, log, config):
        self.log = log
        self.config = config

    def init_opts(self, subparsers):
        fileprovider_parser = subparsers.add_parser('fileprovider', help='Provides a directory via SMB')
        fileprovider_parser.add_argument('-P', '--port', required=False, default=self.default_port, type=int, help=f"Port to use, defaults to {self.default_port}")
        fileprovider_parser.add_argument('-i', '--interface', required=False, help='Network interface to use, use {mod.vpnconnect.args.interface} to reuse VPN interface')
        fileprovider_group = fileprovider_parser.add_mutually_exclusive_group()
        fileprovider_group.add_argument('-d', '--dir', default=self.default_path, type=fileprovider.dir_path, help=f"Directory to share, defaults to {self.default_path}")
        fileprovider_group.add_argument('-f', '--file', type=argparse.FileType('r'), required=False, help=f"File to share")
        fileprovider_parser.add_argument('-s', '--share', required=False, default=self.default_share, help=f"Name of the shared directory, defaults to {self.default_share}")
        fileprovider_parser.add_argument('-u', '--user', default=self.default_username, required=False, help='User name, use {user()} to generate one, defaults to ' + f"{self.default_username}")
        fileprovider_parser.add_argument('-p', '--password', required=False, help='Password, use {passwd()} to generate one')
        fileprovider_parser.add_argument('-w', '--workgroup', required=False, default=self.default_workgroup, help='Workgroup')
        fileprovider_parser.set_defaults(func=self.action)

    def action(self, args):
        def check_service(host, port):
            while True:
                if fileprovider.check_connection(host, port):
                    return

        self.args = args
        if self.log.level == logging.DEBUG:
            self.default_args.append('--debug-stdout')
        if not args.dir.endswith('/'):
            args.dir = args.dir + '/'
        
        try:
            self.parse_templates(args, ['user', 'password'])
            self.build_config(args.port, args.share, args.dir, args.workgroup, args.user)
            if args.user and args.password:
                self.add_user(args.user, args.password)
                self.log.debug(f"Trying to grant ownership of {args.dir} to {args.user}")
                shutil.chown(args.dir, user=args.user)
            cmd = self.build_cmd(args.port)
            self.log.debug(f"Command is '{' '.join(cmd)}'")
        except Exception as e:
            self.log.error(f"Can't write to {self.config_file}")
            self.log.error(e, exc_info=True)
            raise Exception('Failed to setup Samba')
        if not args.interface:
            default_interface = self.primary_interface()
            self.log.debug(f"Default interface '{default_interface}'")
            setattr(args, 'interface', default_interface)

        if args.file is not None:
            args.dir = str(pathlib.Path(args.file).parent)

        setattr(args, 'address', self.list_interfaces()[args.interface][0].ip)
        self.log.debug(f"Binding to {args.address}")
        if self.config['dry_run']:
            self.log.info('Dry run activated, skipping excution')
            return
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            info_func = lambda line: logging.info('Samba message: ' + line)
            threading.Thread(target=self.log_writer, args=[self.proc.stdout, info_func]).start()
            debug_func = lambda line: logging.debug('Samba error: ' + line)
            threading.Thread(target=self.log_writer, args=[self.proc.stderr, debug_func]).start()

            self.log.debug('Waiting for Samba to come up')
            service_ready = threading.Thread(target=check_service, args=[args.address, args.port])
            service_ready.start()
            service_wait = 5
            service_ready.join(service_wait)
            if service_ready.is_alive():
                raise Exception(f"Service '{cmd}' couldn't be set up after {service_wait} seconds")

        except KeyboardInterrupt as ki:
            self.log.warn(f"Shuting down {self.executable}")

    def add_user(self, user, password):
        cmd = ['/usr/bin/smbpasswd', '-a', user]
        self.log.debug(f"Running '{' '.join(cmd)}' to add user, passing password '{password}'")
        if self.config['dry_run']:
            self.log.info('Dry run activated, skipping excution')
            return
        smbpasswd = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE , text=True) #, start_new_session=True
        smbpasswd.communicate(input=password + '\n' + password + '\n')
        if smbpasswd.returncode == 0:
            self.log.debug(f"Set new password for {user}")
        else:
            raise Exception(f"Couldn't set password for user {user}")

    def build_cmd(self, port):
        cmd = [self.executable]
        cmd.extend(self.default_args)
        cmd.extend(['-p', str(port)])
        return cmd
    
    def build_config(self, port, share, path, workgroup, user='', guest='Administrator'):
        config = Template(fileprovider.conf_template).substitute(port=port, share=share, path=path, workgroup=workgroup, user=user, guest=guest)
        if self.config['dry_run']:
            self.log.info('Dry run activated, skipping excution')
            return
        with  open(self.config_file, "w") as config_file:
            config_file.write(config)

    # Based on https://stackoverflow.com/a/35370008
    def check_connection(host, port, timeout = 3):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(timeout)
            if sock.connect_ex((host, port)) == 0:
                return True
            else:
                return False

    def dir_path(path):
        if os.path.isdir(path):
            return path
        else:
            raise argparse.ArgumentTypeError(f"{path} is not a valid directory!")
