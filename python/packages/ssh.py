import paramiko
import logging
import os

Log = logging.getLogger()

class Command(object):
  def __init__(self, stdin=None, stdout=None, stderr=None):
    self.stdin = stdin
    self.stdout = stdout
    self.stderr = stderr


class Connection(object):
  def __init__(self, conn):
    self.host = None
    self.port = None
    if ':' in conn:
      self.host, self.port = conn.split(':')
    else:
      self.host = conn
      self.port = 22
    self.port = int(self.port)


class SshUtils(object):

    @staticmethod
    def _exec(c, cmds, user, host):
        for cmd in cmds:
            Log.info("ssh {}@{}\"{}\"".format(user, host, cmd.stdin))
            stdin, stdout, stderr = c.exec_command(cmd.stdin)
            cmd.stdout = stdout
            cmd.stderr = stderr
            if stdout.channel.recv_exit_status() != 0:
                raise Exception("ERROR : {}\n".format(stderr.read()))

    @staticmethod
    def sftpPut(hostname, user, local, remote, pkeyPath):
        conn = Connection(hostname)
        Log.info(
            "sftp put {} to -p {} {}@{}:{} using pkey {}".format(local, conn.port, user, conn.host, remote, pkeyPath))
        # pkey = readPkey( pkeyPath )
        # print(pkey)
        pkey = paramiko.RSAKey.from_private_key_file(pkeyPath)
        t = paramiko.Transport((conn.host, conn.port))
        # Catch paramiko.AuthenticationException in parent
        t.connect(username=user, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp_res = sftp.put(local, remote)

    @staticmethod
    def sftpGet(hostname, user, remote, local, pkeyPath):
        conn = Connection(hostname)
        Log.info(
            "sftp get -p {} {}@{}:{} to {} using pkey {}".format(conn.port, user, conn.host, remote, local,  pkeyPath))
        # pkey = readPkey( pkeyPath )
        # print(pkey)
        pkey = paramiko.RSAKey.from_private_key_file(pkeyPath)
        t = paramiko.Transport((conn.host, conn.port))
        # Catch paramiko.AuthenticationException in parent
        t.connect(username=user, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp_res = sftp.get(remote, local)

    @staticmethod
    def execute( host, user, commands, **kwargs ):
        conn = Connection(host)
        c = paramiko.SSHClient()
        c.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Catch paramiko.AuthenticationException in parent
        if kwargs.get('passwd', None) is not None:
          Log.debug('Connecting to {} on port {} using passwd'.format(conn.host, conn.port))
          c.connect( conn.host, conn.port, user, kwargs.get('passwd'))
        elif kwargs.get('pKeyPath', None) is not None:
          Log.debug('Connecting to {} on port {} using private key'.format(conn.host, conn.port))
          c.connect(  conn.host, conn.port, user, pkey=paramiko.RSAKey.from_private_key_file( kwargs.get('pKeyPath') ))
        else:
          raise Exception("You should provide either password or private key")
        SshUtils._exec( c, commands, user, host )
