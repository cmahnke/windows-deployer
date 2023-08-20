import sys
try:
    sys.path.append('/usr/local/bin/')
    from wmiexec import *
except ModuleNotFoundError as mnfe:
    import os, pathlib
    ctx = str(pathlib.Path(os.environ['_']).parent)
    sys.path.append(ctx)
    from wmiexec import *

class windowsdeployer:
    default_file_port = 445
    default_remote_loopback = '10.10.10.1'
    default_user = 'Administrator'

    def __init__(self, log, config):
        self.log = log
        self.config = config

    def init_opts(self, subparsers):
        windowsdeployer_parser = subparsers.add_parser('windowsdeployer', help='Runs an installer via WMI')
        windowsdeployer_parser.add_argument('-u', '--user', default=self.default_user, required=True, help=f"User name for remote machine, defaults to {self.default_user}")
        windowsdeployer_parser.add_argument('-p', '--password', required=True, help='Password for remote machine')
        #windowsdeployer_parser.add_argument('-S', '--shell', default=False, action='store_true', help='Set as Windows shell')
        windowsdeployer_parser.add_argument('-t', '--target', required=True, help='Host to deploy to')
        windowsdeployer_parser.add_argument('-f', '--file', required=True, help='File to deploy')
        windowsdeployer_parser.add_argument('-o', '--installation-options', default='', required=False, help='Options for installer on remote machine')
        windowsdeployer_parser.add_argument('-U', '--file-user', required=False, help='User name for file provider, uses the credentails of the target machine, if not given')
        windowsdeployer_parser.add_argument('-Q', '--file-password', required=False, help='Password for file provider, uses the credentails of the target machine, if not given')
        windowsdeployer_parser.add_argument('-P', '--file-port', default=self.default_file_port, type=int, required=False, help='Port to use')
        windowsdeployer_parser.add_argument('-a', '--file-server', required=True, help='Address of the file server')
        windowsdeployer_parser.add_argument('-s', '--file-share', required=True, help='Name of the shared directory')
        windowsdeployer_parser.set_defaults(func=self.action)

    def action(self, args):
        self.args = args
        if not os.path.isfile(args.file):
            raise Exception(f"{args.file} doesn't exist!")
        self.parse_templates(args, ['user', 'password', 'file_user', 'file_password', 'file_share', 'file_port', 'file_server'])

        if args.file_user is None:
            args.file_user = args.user

        if args.file_password is None:
            args.file_password = args.password

        file_server = args.file_server
        if args.file_port != self.default_file_port:
            self.set_remote_port(args.file_port, args.user, args.password, args.target)
            file_server = self.default_remote_loopback

        remote_cmd = self.build_remote_cmd(args.user, args.password, file_server, args.file_share, args.file, args.installation_options)
        self.log.debug("Remote commands are '" + "', '".join(cmd))

        if self.dry_run.config['dry_run']:
            self.log.info('Dry run activated, skipping excution')
            return
        
        for cmd in remote_cmd:
            self.remote_exec(cmd, args.user, args.password, args.target)
        if args.file_port != self.default_file_port:
            self.del_remote_port(args.user, args.password, args.target)
        if args.shell:
            raise NotImplementedError()
            #TODO: Find a way to extract the path of the installed executable
            #self.set_shell('', args.user, args.password, args.target)

    def build_remote_cmd(self, user, password, server, share, file, opts):
        return [fr"net use \\{server}\{share} /user:{user} {password}", fr"\\{server}\{share}\{file} {opts}"]

    def set_shell(self, command, user, password, target):
        remote_cmd = f"reg add \"HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon\" /v Shell /t REG_SZ /d \"{command}\""
        wmiexec = WMIEXEC(command=remote_cmd, username=user, password=password)
        wmiexec.run(target)

    def remote_exec(self, cmd, user, password, target):
        self.log.debug(f"Running {cmd} on {target}")
        wmiexec = WMIEXEC(command=cmd, username=user, password=password)
        wmiexec.run(target)

    def set_remote_port(self, server, port, user, password, target):
        cmd = f"netsh interface portproxy add v4tov4 listenaddress={self.default_remote_loopback} listenport=={self.default_file_port} connectaddress={server} connectport={port}"
        self.remote_exec(self, cmd, user, password, target)

    def del_remote_port(self, user, password, target):
        cmd = f"netsh interface portproxy delete v4tov4 listenaddress={self.default_remote_loopback} listenport={self.default_file_port}"
        self.remote_exec(self, cmd, user, password, target)
