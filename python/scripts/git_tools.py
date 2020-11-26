#!/bin/env python
##########################
#
# Purpose   : Utils to get and push file from git
# Date      : 27/08/2020
#
##########################
import os
from packages.git import GitManager, GitRequests
from optparse import OptionParser
from packages.utils import vaargCallback
import logging
import sys
import base64
import getpass
Log = logging.getLogger()
logging.basicConfig(level = logging.INFO)

if __name__ == '__main__':
    github = 'https://github.com'
    repo = 'myrepo'
    owner = 'myuser'
    token = None
    tokenfile = os.path.join(os.environ.get('TOKEN_FOLDER','~'),'.gittoken')
    if os.path.isfile(tokenfile):
        f = open(tokenfile, 'r')
        token = f.read().rstrip()
        f.close()
    branch = 'master'

    user = None
    passwd = None

    if token is None:
        user = raw_input("User : ")
        passwd =  getpass.getpass("Passwd : ")
        #user = '***'
        #passwd = '***'


    gr = GitRequests(github, token, user, passwd)
    gm = GitManager(gr)
    parser = OptionParser()
    parser.add_option("-p", "--put", dest="put", action="callback", callback=vaargCallback, help="Put a file")
    parser.add_option("-g", "--get", dest="get", action="callback", callback=vaargCallback, help="Get a file")
    parser.add_option("-r", "--repo", action="store", type="string", help="Repo")
    parser.add_option("-o", "--owner", action="store", type="string", help="Owner")
    parser.add_option("-b", "--branch", action="store", type="string", help="Branch")
    parser.add_option("-l", "--list", action="store_true", default=False, help="List file on repo")
    parser.add_option("-f", "--force", action="store_true", default=False, help="Do not ask to overwrite the file")
    (options, args) = parser.parse_args()
    if options.owner:
        owner = options.owner

    if options.repo:
        repo = options.repo

    if options.branch:
        branch = options.branch

    if options.list:
        tree = gm.get_branch_tree(branch, repo, owner)
        for element in tree.get('tree'):
            print('{0}'.format(element.get('path')))

    if options.put:
        for file in options.put:
            Log.info("Put {}".format(file))
            gm.update_content(branch, repo, owner, file, file, "put {0}".format(file))

    if options.get:
        for file in options.get:
            if os.path.isfile(os.path.basename(file)) and not options.force:
                Log.warn('{0} already exists, do you want to overwrite it ? '.format(os.path.basename(file)))
                answer = raw_input("y/n ")
                if answer.lower() != 'y':
                    continue
                    Log.warn('Bypassing {0}'.format(os.path.basename(file)))
            Log.info("Get {}".format(file))
            resp = gm.get_path_content(branch, repo, owner, file)
            content = base64.decodestring(resp['content'])
            f = open(os.path.join(os.getcwd(), os.path.basename(file)), 'w')
            f.write(content)
            f.close()
            if os.path.isfile(os.path.basename(file)):
                Log.info("{0} successfully retrieved".format(file))
            else:
                Log.error("{0} NOT retrieved".format(file))
