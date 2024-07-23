#!/usr/bin/env python3

from pathlib import Path
from importlib import import_module
from io import StringIO
from collections import OrderedDict
import argparse, logging, sys, threading, os, time, random, string, shutil
import ifaddr
from dotmap import DotMap


lib_dir = 'lib'
default_log_level = logging.WARN

class subcommand:
    def setModules(self, modules):
        self.modules = modules

    def parse_templates(self, args, keys):
        for key in keys:
            if getattr(args, key) is not None:
                val = str(getattr(args, key, ''))
                if val.find('{') < val.find('}'):
                    try:
                        setattr(args, key, eval('f"' + val + '"', {}, self.template_helpers()))
                        self.log.debug(f"Rewritten {key} is '{getattr(args, key, '')}', was: '{val}'")
                    except (ModuleNotFoundError, SyntaxError, AttributeError) as e:
                        self.log.error(f"Can't evaluate '{val}'")
                        self.log.error(e, exc_info=True)
                        raise Exception('Processing failed!')
    
    def user(self, n=6):
        return ''.join(random.choices(string.ascii_lowercase, k=n))

    def passwd(self, n=10):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

    def filename(self, path):
        return Path(path).name

    def stop(self):
        def kill(proc):
            if isinstance(proc, threading.Thread):
                proc.join()
            else:
                proc.terminate()
                proc.wait()
        if 'proc' in dir(self) and self.proc is not None:
            if isinstance(self.proc, list):
                for p in self.proc:
                    kill(p)
            else:
                kill(self.proc)

    def template_helpers(self):
        return {'user': self.user, 'passwd': self.passwd, 'filename': self.filename,  'mod': self.modules}
    
    def primary_interface(self):
        return list(ifaddr.get_adapters())[1].name

    def list_interfaces(self):
        adapters = OrderedDict()
        for adapter in ifaddr.get_adapters():
            adapters[adapter.name] = adapter.ips
        return adapters

    def log_writer(self, pipe, func):
        with pipe:
            for line in iter(pipe.readline, b''):
                line = line.decode('utf-8').strip()
                func(line)

    def set_debug(self, script):
        with open(script) as script_file:
            lines = script_file.readlines()
            first_line = lines[0].strip()
            if 'sh' in lines[0] and not '-x' in lines[0]:
                lines[0] = first_line + ' -x\n'
            elif 'python' in lines[0] and not '-d' in lines[0]:
                lines[0] = first_line + ' -d\n'
        if lines[0] is not first_line:
            with open(script, "w") as script_file:
                self.log.debug(f"Rewriting {first_line} to {lines[0].strip()} (with line break) in {script}")
                script_file.writelines(lines)
    
    # See https://stackoverflow.com/a/52614708
    class formatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
        columns = shutil.get_terminal_size().columns

def group_args(argv, modules):
    current_subcmd = 0
    subcmds = []
    subcmds.append([])
    for a in argv:
        if a in modules.keys():
            current_subcmd += 1
            subcmds.append([])
        subcmds[current_subcmd].append(a)
    if len(subcmds) == 1:
        return [subcmds[0]]
    elif len(subcmds) == 2:
        return [subcmds[0] + subcmds[1]]
    else:
        return [subcmds[0] + subcmds[1], *subcmds[2:]]

def load_config(cfg):
    with open(cfg, 'r') as file:
        if cfg.lower().endswith('.toml'):
            import toml
            return toml.load(cfg)
        elif cfg.lower().endswith('.yml') or cfg.lower().endswith('.yaml'):
            import yaml
            return yaml.load(cfg)
        else:
            raise NotImplementedError()

def load_modules(lib_dir, logger, dry_run):
    modules = {}
    for file in Path(__file__).parent.glob(f"{lib_dir}/*.py"):
        if "__" not in file.stem:
            logger.debug(("Loading file {} as {}".format(str(file), file.stem)))
            try:
                mod = import_module(f"{lib_dir}.{file.stem}", __package__)
                modules[file.stem] = getattr(mod, file.stem)(logger, dry_run)
                modules[file.stem].__class__ = type(file.stem + 'Subcommand', (getattr(mod, file.stem), subcommand), {})
                logger.debug(f"Added Module {file.stem}, type {modules[file.stem]}")
            except Exception as e:
                logger.debug(e, exc_info=True)
                logger.error(f"Failed to import {file.stem}")
    return DotMap(modules)

def main():
    logger = logging.getLogger()
    log_stream = StringIO()
    config = {'dry_run': False}
    logging.basicConfig(stream=log_stream, level=logging.DEBUG)
    modules = load_modules(lib_dir, logger, config)
    columns = shutil.get_terminal_size().columns
    parser = argparse.ArgumentParser(prog='run.py', description='Performs commands of sub modules',
                                     formatter_class=lambda prog: subcommand.formatter(prog, width=columns, indent_increment=2, max_help_position=int(columns/2)))
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable logging')
    parser.add_argument('-w', '--wait', type=int, default=30, help='Wait time before shutdown')
    parser.add_argument('-d', '--dry-run', action='store_true', help="Don't execute generated commands")
    parser.add_argument('-c', '--config', type=argparse.FileType('r'), required=False, help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers()

    for mod in modules.values():
        mod.init_opts(subparsers)
        mod.setModules(modules)

    if len(sys.argv) > 1:
        arg_groups = group_args(sys.argv[1:], modules)
    else:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(arg_groups[0])
    if len(arg_groups) == 1 and 'dry_run' in vars(args) and 'verbose' in vars(args) and 'wait' in vars(args) and len(vars(args)) <= 3:
        parser.print_help()
        sys.exit(0)
    if args.config:
        config = load_config(args.config)
    if args.verbose:
        print(log_stream.getvalue(), end='')
    else:
        logger.setLevel(default_log_level)
    logging.basicConfig(stream=sys.stdout, force=True)
    if args.dry_run:
        config['dry_run'] = True
        logger.debug('Dry run enabled')
    timeout = args.wait
    args.func(args)

    # Parse trailing subcommands
    if len(arg_groups) > 1:
        for arg_group in arg_groups[1:]:
            args = parser.parse_args(arg_group)
            #logger.debug(f"Chained command {args}")
            args.func(args)

    if timeout < 5:
        timeout = 5
    logger.debug(f"Waiting {timeout} seconds...")
    try:
        time.sleep(timeout)
    except KeyboardInterrupt as ki:
        logger.warning(f"Force quiting")

    logger.debug('Cleaning up')
    for mod in modules.keys():
        logger.debug(f"Stopping module {mod}")
        modules[mod].stop()

    logger.debug('Processing finished')

if __name__ == "__main__":
    main()
