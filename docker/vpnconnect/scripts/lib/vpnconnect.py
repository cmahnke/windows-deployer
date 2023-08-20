import subprocess, logging, threading, re, os, time

class vpnconnect():
    default_args = ['--protocol=anyconnect', '--no-dtls', '--disable-ipv6', '--passwd-on-stdin', '--non-inter'] #, '-b', 
    executable = '/usr/bin/openconnect'
    vpnc_script = '/etc/vpnc/vpnc-script'
    default_interface = 'tun0'

    def __init__(self, log, config):
        self.log = log
        self.config = config

    def init_opts(self, subparsers):
        vpnconnect_parser = subparsers.add_parser('vpnconnect', help='Connects to a Cisco Anyconnect VPN service')
        vpnconnect_parser.add_argument('-u', '--user', required=True, help='User name')
        vpnconnect_parser.add_argument('-p', '--password', required=True, help='Password')
        #vpnconnect_parser.add_argument('-c', '--certificate', required=False, help='Certificate')
        vpnconnect_parser.add_argument('-i', '--interface', default=self.default_interface, help=f"Interface to bind to, defaults to {self.default_interface}")
        vpnconnect_parser.add_argument('-s', '--server', required=True, help="Server to connect to")
        vpnconnect_parser.set_defaults(func=self.action)

    def action(self, args):
        def check_output(pipe, func_handle, func_condition):
            for line in iter(pipe.readline, b''):
                line = line.decode('utf-8').strip()
                func_handle(line)
                if (bool(func_condition(line))):
                    break
            return
        
        def check_iface(iface):
            while True:
                if iface in self.list_interfaces():
                    return

        self.args = args
        if self.log.level == logging.DEBUG:
            #self.set_debug(self.vpnc_script)
            self.default_args.append('-v')

        cmd = self.build_cmd(args.user, args.server, args.interface)
        self.log.debug(f"Running command '{' '.join(cmd)}'")

        if self.config['dry_run']:
            self.log.info('Dry run activated, skipping excution')
            return

        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
        self.proc.stdin.write(f"{args.password}\n".encode())
        self.proc.stdin.flush()
        info_func = lambda line: logging.info('OpenConnect message: ' + line)
        checker_func = lambda line: re.search(r'Configured as .* with .* connected', line)
        checker_thread = threading.Thread(target=check_output, args=[self.proc.stdout, info_func, checker_func])
        checker_thread.start()
        debug_func = lambda line: logging.debug('OpenConnect error: ' + line)
        threading.Thread(target=self.log_writer, args=[self.proc.stderr, debug_func]).start()
        checker_thread.join()
        self.log.debug(f"Connected to server {args.server} as {args.user}")
        threading.Thread(target=self.log_writer, args=[self.proc.stdout, info_func]).start()

        args.interface = self.default_interface        
        try:
            iface_ready = threading.Thread(target=check_iface, args=[args.interface])
            iface_ready.start()
            iface_wait = 5
            iface_ready.join(iface_wait)
            if iface_ready.is_alive():
                raise Exception(f"Interface {args.interface} couldn't be set up after {iface_wait} seconds")
            self.log.debug(f"Default interface '{args.interface}' is ready")
            setattr(args, 'address', self.list_interfaces()[args.interface][0].ip)
            self.log.debug(f"Binding to {args.address}")
        except KeyError:
            import ifaddr
            self.log.warn(f"Can't get address for {args.interface}, available interfaces are {self.list_interfaces()}")
            self.log.debug(f"RAW {ifaddr.get_adapters(include_unconfigured=True)}")
            os.system('ifconfig')
            os.system('pstree -p')
            os.system('route')

    def build_cmd(self, user, server, interface):
        cmd = [self.executable]
        cmd.extend(self.default_args)
        cmd.extend(['-i', interface, f"--script={self.vpnc_script}"])
        cmd.extend(['-u', user, server])
        return cmd
