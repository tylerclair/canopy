import urllib.parse
import requests


class CanvasAPIError(Exception):
    def __init__(self, response):
        self.response = response

    def __unicode__(self):
        return 'API Request Failed. Status: {} Content: {}'.format(self.response.status_code, self.response.content)

    def __str__(self):
        return 'API Request Failed. Status: {} Content: {}'.format(self.response.status_code, self.response.content)


class CanvasClient(object):
    def __init__(self, instance_address, access_token, catalog=False):
        if catalog:
            self.instance_address = instance_address
            self.access_token = access_token
            self.session = requests.session()
            self.session.headers.update({'Authorization': 'Token token=\"{}\"'.format(self.access_token)})
        else:
            self.instance_address = instance_address
            self.access_token = access_token
            self.session = requests.session()
            self.session.headers.update({'Authorization': 'Bearer {}'.format(self.access_token)})

    @staticmethod
    def extract_data_from_response(response, data_key=None):
        response_json_data = response.json()
        if type(response_json_data) == list:
            # Return the data
            return response_json_data
        elif type(response_json_data) == dict:
            if data_key is None:
                return response_json_data
            else:
                return response_json_data[data_key]
        else:
            raise CanvasAPIError(response)

    @staticmethod
    def extract_pagination_links(response):
        try:
            link_header = response.links
        except KeyError:
            return None
        return link_header

    @staticmethod
    def has_pagination_links(response):
        return 'Link' in response.headers

    def depaginate(self, response, data_key=None):
        all_data = []
        this_data = self.extract_data_from_response(response, data_key=data_key)
        if this_data is not None:
            if type(this_data) == list:
                all_data += this_data
            else:
                all_data.append(this_data)

        if self.has_pagination_links(response):
            pagination_links = self.extract_pagination_links(response)
            try:
                while pagination_links['next']:
                    response = self.session.get(pagination_links['next']['url'])
                    pagination_links = self.extract_pagination_links(response)
                    this_data = self.extract_data_from_response(response, data_key=data_key)
                    if this_data is not None:
                        if type(this_data) == list:
                            all_data += this_data
                        else:
                            all_data.append(this_data)
            except KeyError:
                pass
        else:
            return 'Response from {} has no pagination links.'.format(response.url)
        return all_data

    def base_request(self,
                     method,
                     uri,
                     data_key=None,
                     data=None,
                     params=None,
                     single_item=False,
                     all_pages=False,
                     do_not_process=False,
                     no_data=False,
                     force_urlencode_data=False,
                     allow_redirects=True):
        if not uri.startswith('http'):
            uri = self.instance_address + uri

        if force_urlencode_data is True:
            uri += '?' + urllib.parse.urlencode(data)

        if method == 'GET':
            response = self.session.get(uri, params=params, allow_redirects=allow_redirects)
        elif method == 'POST':
            response = self.session.post(uri, data=data, allow_redirects=allow_redirects)
        elif method == 'PUT':
            response = self.session.put(uri, data=data, allow_redirects=allow_redirects)
        elif method == 'DELETE':
            response = self.session.delete(uri, params=params, allow_redirects=allow_redirects)
        else:
            response = self.session.get(uri, params=params, allow_redirects=allow_redirects)

        response.raise_for_status()

        if single_item:
            r = response.json()
            if data_key:
                return r[data_key]
            else:
                return r
        if all_pages:
            return self.depaginate(response, data_key)
        if do_not_process:
            return response
        if no_data:
            return response.status_code()
        return response.json()

    def get(self, url, params=None, **kwargs):
        kwargs.setdefault('allow_redirects', True)
        return self.base_request('GET', url, params=params, **kwargs)

    def post(self, url, data=None, **kwargs):
        kwargs.setdefault('allow_redirects', True)
        return self.base_request('POST', url, data=data, **kwargs)

    def put(self, url, data=None, **kwargs):
        kwargs.setdefault('allow_redirects', True)
        return self.base_request('PUT', url, data=data, **kwargs)

    def delete(self, url, params=None, **kwargs):
        kwargs.setdefault('allow_redirects', True)
        return self.base_request('DELETE', url, params=params, **kwargs)
