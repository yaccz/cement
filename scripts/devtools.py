#!/usr/bin/env python

import os
import sys
import re
import tempfile

from cement.core.foundation import CementApp
from cement.core.controller import CementBaseController, expose
from cement.utils.version import get_version
from cement.utils import shell

VERSION = get_version()

class CementDevtoolsController(CementBaseController):
    class Meta:
        label = 'base'
        arguments = [
            (['-y, --noprompt'], 
             dict(help='answer yes to prompts.', action='store_true', 
                  dest='noprompt')),
            (['--ignore-errors'],
             dict(help="don't stop operations because of errors", 
                  action='store_true', dest='ignore_errors')),
            (['--loud'], dict(help='add more verbose output', 
             action='store_true', dest='loud')),
            (['modifier1'], 
             dict(help='command modifier positional argument', nargs='?')),
        ]
        
    def _do_error(self, msg):
        if self.app.pargs.ignore_errors:
            self.app.log.error(msg)
        else:
            raise Exception(msg)
            
    @expose(hide=True) 
    def default(self):
        raise AssertionError("A sub-command is required.  See --help.")
        
    def _do_git(self):
        # make sure we don't have any uncommitted changes
        print('Checking for Uncommitted Changes')
        out, err, res = shell.exec_cmd(['git', '--no-pager', 'diff'])
        if len(out) > 0:
            self._do_error('There are uncommitted changes. See `git status`.')
        
        # make sure we don't have any un-added files
        print('Checking for Untracked Files')
        out, err, res = shell.exec_cmd(['git', 'status'])
        if re.match('Untracked files', out):
            self._do_error('There are untracked files.  See `git status`.')
                
        # make sure there isn't an existing tag
        print("Checking for Duplicate Git Tag")
        out, err, res = shell.exec_cmd(['git', 'tag'])
        for ver in out.split('\n'):
            if ver == VERSION:
                self._do_error("Tag %s already exists" % VERSION)
        
        print("Tagging Git Release")
        out, err, res = shell.exec_cmd(['git', 'tag', '-a', '-m', VERSION, 
                                        VERSION])
        if res > 0:
            self._do_error("Unable to tag release with git.")

    def _do_tests(self):
        print('Running Nose Tests')
        out, err, res = shell.exec_cmd(['which', 'nosetests'])
        
        if self.app.pargs.loud:
            cmd_args = ['coverage', 'run', out.strip(), '--verbosity=3']
            res = shell.exec_cmd2(cmd_args)
        else:
            cmd_args = ['coverage', 'run', out.strip(), '--verbosity=0']
            out, err, res = shell.exec_cmd(cmd_args)
        if res > 0:
            self._do_error("\n\nNose tests did not pass.\n\n" +
                           "$ %s\n%s" % (' '.join(cmd_args), err))
        
    def _do_pep8(self):
        print("Checking PEP8 Compliance")
        cmd_args = ['pep8', '-r', 'cement/', '--exclude=*.pyc']
        out, err, res = shell.exec_cmd(cmd_args)
        if res > 0:
            self._do_error("\n\nPEP8 checks did not pass.\n\n" +
                           "$ %s\n%s" % (' '.join(cmd_args), out))

    @expose(help='run all unit tests')
    def run_tests(self):
        print('')
        print(("Running Tests for Cement Version %s" % VERSION))
        print(('-' * 77))
        self._do_pep8()
        self._do_tests()
        print('')

    def _do_sphinx(self, dest_path):
        print("Building Documentation")
        cmd_args = ['rm', '-rf', 'docs/build/*']
        cmd_args = ['sphinx-build', 'doc/source', dest_path]
        out, err, res = shell.exec_cmd(cmd_args)
        if res > 0:
            self._do_error("\n\nFailed to build sphinx documentation\n\n" +
                           "$ %s\n%s" % (' '.join(cmd_args), out))
                           
    @expose(help='create a cement release')
    def make_release(self):
        print('')
        print(("Making Release for Version %s" % VERSION))
        print(('-' * 77))
        if not self.app.pargs.noprompt:
            res = eval(input("Continue? [yN] "))
            if res not in ['Y', 'y', '1']:
                sys.exit(1)
        
        tmp = tempfile.mkdtemp()
        print(("Destination: %s" % tmp))
        os.makedirs(os.path.join(tmp, 'source'))
        os.makedirs(os.path.join(tmp, 'doc'))
        
        self._do_pep8()
        self._do_tests()
        self._do_git()
        self._do_sphinx(os.path.join(tmp, 'doc'))
        
        tar_path = os.path.join(tmp, 'source', 'cement-%s.tar' % VERSION)
        gzip_path = "%s.gz" % tar_path
        
        print("Generating Release Files")
        cmd_args = ['git', 'archive', VERSION, 
                    '--prefix=cement-%s/' % VERSION,
                    '--output=%s' % tar_path]
        out, err, res = shell.exec_cmd(cmd_args)
        
        cmd_args = ['gzip', tar_path]
        out, err, res = shell.exec_cmd(cmd_args)
        if res > 0:
            self._do_error("\n\nFailed generating git archive.\n\n" +
                           "$ %s" % (' '.join(cmd_args), err))

        print('')
        
    @expose(help='get the current version of the sources')
    def get_version(self):
        print(VERSION)
        
class CementDevtoolsApp(CementApp):
    class Meta:
        label = 'cement-devtools'
        base_controller = CementDevtoolsController
        
                
def main():
    app = CementDevtoolsApp('cement-devtools')
    try:
        app.setup()
        app.run()
    except AssertionError as e:
        print(("AssertionError => %s" % e.args[0]))
    finally:
        app.close()

if __name__ == '__main__':
    main()