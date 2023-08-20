from smbclient import listdir, stat, register_session
import smbprotocol

class verify:
    default_port = 445
    default_username = 'Guest'
    default_passwort = ''

    def __init__(self, log, config):
        self.log = log
        self.config = config

    def init_opts(self, subparsers):
        verify_parser = subparsers.add_parser('verify', help='Checks if file service can be reached')
        verify_parser.add_argument('-f', '--file', default="", required=False, help='File to deploy')
        verify_parser.add_argument('-P', '--port', type=int, default=self.default_port, required=False, help=f"Port to use, defaults to {self.default_port}")
        verify_parser.add_argument('-a', '--address', required=True, help='Address of the file server')
        verify_parser.add_argument('-s', '--share', required=True, help='Name of the shared directory')
        verify_parser.add_argument('-u', '--user', required=False, default=self.default_username, help='User name, use {mod.fileprovider.args.user} to use the generated')
        verify_parser.add_argument('-p', '--password', required=False, default=self.default_passwort, help='Password, use {mod.fileprovider.args.password} to use the generated')
        verify_parser.set_defaults(func=self.action)

    def action(self, args):
        self.parse_templates(args, ['user', 'password', 'file', 'share', 'port', 'address'])
        if self.config['dry_run']:
            self.log.info('Dry run activated, skipping excution')
            return
        try:
            register_session(args.address, username=args.user, password=args.password, port=args.port)
            for filename in listdir(f"\\\\{args.address}\\{args.share}\\"):
                self.log.info(filename)
            if args.file and not stat(f"\\\\{args.address}\\{args.share}\\{args.file}"):
                self.log.error(f"\\\\{args.address}\\{args.share}\\{args.file} not found!")
                raise FileNotFoundError(f"\\\\{args.address}\\{args.share}\\{args.file} not found!")
        except smbprotocol.exceptions.SMBAuthenticationError as smbe:
            self.error('You need to provide a password')
        except Exception as e:
            self.log.error(e, exc_info=True)


            
