from mr.developer import common
import os
import subprocess


logger = common.logger


class GitError(common.WCError):
    pass


class GitWorkingCopy(common.BaseWorkingCopy):
    def git_switch_branch(self, source, stdout, stderr):
        name = source['name']
        path = source['path']
        branch = source['branch']
        # This should go smoothly for both existing local mirrors and for
        # unexisting ones: git automagically creates the local branch if it
        # sees it exists in the origin
        cmd = subprocess.Popen(["git", "checkout", branch],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        local_stdout, local_stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git checkout of branch '%s' failed.\n%s" % (branch, stderr))
        return (stdout + local_stdout,
                stderr + local_stderr)

    def git_checkout(self, source, **kwargs):
        name = source['name']
        path = source['path']
        url = source['url']
        branch = source.get('branch', None)
        if os.path.exists(path):
            self.output((logger.info, "Skipped cloning of existing package '%s'." % name))
            return
        self.output((logger.info, "Cloning '%s' with git." % name))
        argv = ["git", "clone", "--quiet", url, path]
        if branch is not None:
            # I'm not too willing to go into the oddities of this, but to check
            # out a branch via subprocess.Popen you have to pass the parameter
            # without the space
            argv.insert(2, '-b%s' % branch)
        cmd = subprocess.Popen(argv,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git cloning for '%s' failed.\n%s" % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def git_update(self, source, **kwargs):
        name = source['name']
        path = source['path']
        self.output((logger.info, "Updating '%s' with git." % name))
        cmd = subprocess.Popen(["git", "pull"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git pull for '%s' failed.\n%s" % (name, stderr))
        if 'branch' in source:
            stdout, stderr = self.git_switch_branch(source, stdout, stderr)
        if kwargs.get('verbose', False):
            return stdout

    def checkout(self, source, **kwargs):
        name = source['name']
        path = source['path']
        update = self.should_update(source, **kwargs)
        if os.path.exists(path):
            if update:
                self.update(source, **kwargs)
            elif self.matches(source):
                self.output((logger.info, "Skipped checkout of existing package '%s'." % name))
            else:
                raise GitError("Checkout URL for existing package '%s' differs. Expected '%s'." % (name, source['url']))
        else:
            return self.git_checkout(source, **kwargs)

    def matches(self, source):
        name = source['name']
        path = source['path']
        cmd = subprocess.Popen(["git", "remote", "-v"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git remote for '%s' failed.\n%s" % (name, stderr))
        return (source['url'] in stdout.split())

    def status(self, source, **kwargs):
        name = source['name']
        path = source['path']
        cmd = subprocess.Popen(["git", "status"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        lines = stdout.strip().split('\n')
        if 'nothing to commit (working directory clean)' in lines[-1]:
            status = 'clean'
        else:
            status = 'dirty'
        if kwargs.get('verbose', False):
            return status, stdout
        else:
            return status

    def update(self, source, **kwargs):
        name = source['name']
        path = source['path']
        if not self.matches(source):
            raise GitError("Can't update package '%s', because it's URL doesn't match." % name)
        if self.status(source) != 'clean' and not kwargs.get('force', False):
            raise GitError("Can't update package '%s', because it's dirty." % name)
        return self.git_update(source, **kwargs)

common.workingcopytypes['git'] = GitWorkingCopy
