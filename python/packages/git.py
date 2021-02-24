import logging
import os
import json
import urllib
import urllib2
import zipfile
import base64

from packages.utils import Utils

Log = logging.getLogger()


class GitManager(object):
    def __init__(self, git_request=None):
        self.git_request = git_request

    def get_commits(self, f_branch, f_repo, f_owner):
        # resp = gr.get(short_url='/api/v3/repositories')
        resp = self.git_request.get(short_url='/api/v3/repos/{0}/{1}/commits/{2}'.format(
            f_owner, f_repo, f_branch)).read()
        json_data = json.loads(resp)
        return json_data

    def pull_request(self, base_branch, head_branch, f_repo, f_owner, text="My pull", title="Title"):
        data = {"base" : base_branch, "head" : head_branch, "title" : title }
        #params = urllib.urlencode(data)
        #resp = self.git_request.post(short_url='/api/v3/repos/{0}/{1}/pulls?{2}'.format(f_owner, f_repo, params)).read()
        resp = self.git_request.post(data=data, short_url='/api/v3/repos/{0}/{1}/pulls'.format(f_owner, f_repo)).read()
        Log.info("Branch creation response : {0}".format(resp))
        json_data = json.loads(resp)
        return json_data

    def get_branch_tree(self, f_branch, f_repo, f_owner):
        # resp = gr.get(short_url='/api/v3/repositories')
        resp = self.git_request.get(short_url='/api/v3/repos/{0}/{1}/branches/{2}'.format(
            f_owner, f_repo, f_branch)).read()
        root_files = json.loads(resp)
        # Get the root tree sha
        root_tree_sha = root_files['commit']['commit']['tree']['sha']
        resp = self.git_request.get(short_url='/api/v3/repos/{0}/{1}/git/trees/{2}'.format(f_owner, f_repo, root_tree_sha),
                                    data={'recursive': 'true'}).read()
        root_tree = json.loads(resp)
        return root_tree

    def download_repo_archive(self, f_branch, f_repo, f_owner, f_dst_folder, download_format='zipball'):
        # resp = gr.get(short_url='/api/v3/repositories')
        Utils.clean_directory(f_dst_folder)
        resp = self.git_request.get(short_url='/api/v3/repos/{0}/{1}/{2}/{3}'.format(f_owner, f_repo, download_format, f_branch)).read()
        f = open(os.path.join(f_dst_folder, '{0}.zip'.format(f_repo)), 'wb')
        f.write(resp)
        f.close()
        with zipfile.ZipFile(os.path.join(f_dst_folder, '{0}.zip'.format(f_repo)), 'r') as _zip:
            _zip.extractall(f_dst_folder)

    @staticmethod
    def get_code_repo(f_repo, f_owner, f_folder):
        files = os.listdir(f_folder)
        # Get only unzipped folder
        files = [f for f in files if "{0}-{1}".format(f_owner, f_repo) in f]
        if len(files) != 1:
            raise RuntimeError("Impossible to find an unzipped repo")
        return os.path.join(f_folder, files[0])

    def get_list_of_repo(self, f_search, f_repo_filter=None):
        all_repo = []
        current_res = 1
        n = 1
        while current_res > 0:
            resp = self.git_request.get(short_url='/api/v3/search/repositories',
                                        data={'q': f_search, 'per_page': 100, 'page': n}).read()
            paged_repo = json.loads(resp)
            current_repo = paged_repo.get('items')
            if f_repo_filter:
                current_repo = [c for c in current_repo if f_repo_filter in c['name']]
            all_repo += current_repo
            current_res = len(paged_repo.get('items'))
            n += 1
        return all_repo

    def get_path_content(self, f_branch, f_repo, f_owner, f_path):
        resp = self.git_request.get(short_url='/api/v3/repos/{0}/{1}/contents/{2}'.format(f_owner, f_repo, f_path),
                                    data={'ref': f_branch}).read()
        return json.loads(resp)


    def update_content(self, f_branch, f_repo, f_owner, f_filepath, f_git_path, f_commit_msg):
        Log.info("Updating {0}/{1}@{2}/{3} with {3} ({5})".format(
            f_owner, f_repo, f_branch, f_git_path, f_filepath, f_commit_msg))
        file = open(f_filepath, mode='r')
        file_content = file.read()
        file.close()
        post_data = {"message": f_commit_msg, "content": base64.encodestring(file_content), "branch": f_branch}

        try:
            resp = self.git_request.get(data={"ref": f_branch},
                                    short_url='/api/v3/repos/{0}/{1}/contents/{2}'.format(f_owner, f_repo, f_git_path))
            # if file exist we need to refer the exising sha
            if resp.code == 200:
                resp = json.loads(resp.read())
                post_data.update({'sha': resp['sha']})
        except:
            Log.debug("{0} does not exist yet".format(file))

        resp = self.git_request.put(data=post_data,
                                    short_url='/api/v3/repos/{0}/{1}/contents/{2}'.format(f_owner, f_repo, f_git_path, f_branch))
        if resp.code >= 200 and resp.code < 300:
            Log.info("{0}/{1}@{2}:{3} successfully update with content of {4}".format(
                f_owner, f_repo, f_branch, f_git_path, f_filepath))
        else:
            msg = "{0}/{1}@{2}:{3} not successfully updated with content of {4} ({5})".format(
                f_owner, f_repo, f_branch, f_git_path, f_filepath, resp.read())
            Log.error("{0}".format(msg))
            raise RuntimeError(msg)
        return resp

    def delete_branch(self, _branch, _repo, _owner):
        resp = self.git_request.delete(short_url='/api/v3/repos/{0}/{1}/git/refs/heads/{2}'.format(_owner, _repo, _branch))
        if resp.code == 204:
            Log.info("Branch {0} succesfully deleted".format(_branch))
        else:
            msg = "Error while deleting branch {0}".format(_branch)
            Log.error(msg)
            raise RuntimeError(msg)
        return resp.read()

    def create_branch_from(self, _from_branch, _to_branch, _repo, _owner):
        branch_created = False
        try:
            resp = self.git_request.get(short_url='/api/v3/repos/{0}/{1}/git/refs/heads/{2}'.format(
                _owner, _repo, _to_branch)).read()
            json_data = json.loads(resp)
            if json_data['ref'] == 'refs/heads/{0}'.format(_to_branch):
                Log.info("Branch {0} already created".format(_to_branch))
                branch_created = True
        except urllib2.HTTPError as e:
            if e == 'HTTP Error 404: Not Found':
                print('Need to create branch {0}'.format(_to_branch))

        if branch_created is False:
            resp = self.git_request.get(short_url='/api/v3/repos/{0}/{1}/git/refs/heads/{2}'.format(
                _owner, _repo, _from_branch)).read()
            json_data = json.loads(resp)
            sha = json_data['object']['sha']
            resp = self.git_request.post(data={
                "ref": "refs/heads/{0}".format(_to_branch),
                "sha": "{0}".format(sha)
                }, short_url='/api/v3/repos/{0}/{1}/git/refs'.format(_owner, _repo)).read()
            Log.info("Branch creation response : {0}".format(resp))
            resp_data = json.loads(resp)
            #  Double check creation of branch
            if resp_data['ref'] == 'refs/heads/{0}'.format(_to_branch):
                Log.info("Branch {0} created".format(_to_branch))


class GitRequests(object):
    def __init__(self, base_url, git_token=None, user=None, passw=None):
        self.base_url = base_url
        self.token = git_token
        self.next_link = None
        self.headers = None
        self.completeUrl = None
        self.user = user
        self.passw = passw
        self.buid_header()

    def buid_header(self):
        if self.token is not None:
            self.headers = {"Authorization": "token {0}".format(self.token)}
        elif self.user is not None and self.passw is not None:
            self.headers = {"Authorization": "Basic %s" % base64.b64encode('%s:%s' % (self.user, self.passw))}
        else:
            raise RuntimeError("No auth method provided. Use either Basic or Token")


    def _geturl(self, short_url=None, full_url=None):
        if full_url is None:
            self.completeUrl = '{0}{1}'.format(self.base_url, short_url)
        else:
            self.completeUrl = full_url
        return self.completeUrl

    def get(self, data=None, short_url=None, full_url=None):
        self._geturl(short_url, full_url)
        if data is not None:
            data = urllib.urlencode(data)
        self.completeUrl = self.completeUrl + '{0}'.format('?' + data if data is not None else '')

        Log.info('GET {0}'.format(self.completeUrl))
        req = urllib2.Request(self.completeUrl, None, self.headers)
        response = urllib2.urlopen(req)
        if hasattr(response, 'links') and 'next' in response.links:
            self.next_link = response.links['next']
        return response

    def _build_request(self, req_type='GET'):
        req = urllib2.Request(self.completeUrl, None, self.headers)
        req.add_header('Content-Type', 'application/json')
        req.get_method = lambda: req_type
        return req

    def post(self, data=None, short_url=None, full_url=None):
        self._geturl(short_url, full_url)
        Log.info('POST {0}'.format(self.completeUrl))
        req = self._build_request('POST')
        response = urllib2.urlopen(req, json.dumps(data))
        if hasattr(response, 'links') and 'next' in response.links:
            self.next_link = response.links['next']
        return response

    def put(self, data=None, short_url=None, full_url=None):
        self._geturl(short_url, full_url)
        Log.info('PUT {0} with data {1}'.format(self.completeUrl, json.dumps(data)))
        req = self._build_request('PUT')
	response = None
        response = urllib2.urlopen(req, json.dumps(data))
        if hasattr(response, 'links') and 'next' in response.links:
            self.next_link = response.links['next']
        return response

    def delete(self, data=None, short_url=None, full_url=None):
        self._geturl(short_url, full_url)
        Log.info('DELETE {0}'.format(self.completeUrl))
        req = self._build_request('DELETE')
        if data is not None:
            response = urllib2.urlopen(req, json.dumps(data))
        else:
            response = urllib2.urlopen(req)
        if hasattr(response, 'links') and 'next' in response.links:
            self.next_link = response.links['next']
        return response
