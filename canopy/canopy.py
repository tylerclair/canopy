import asyncio
import urllib.parse
import json
import requests


class CanvasSession(object):
    def __init__(self, instance_address, access_token, max_per_page=100):
        self.instance_address = instance_address
        self.access_token = access_token
        self.max_per_page = max_per_page
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def extract_data_from_response(self, response, data_key=None):
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

    def extract_pagination_links(self, response):
        try:
            link_header = response.links
        except KeyError:
            return None
        return link_header

    def has_pagination_links(self, response):
        return "Link" in response.headers

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
                while pagination_links["next"]:
                    response = self.session.get(pagination_links["next"]["url"])
                    pagination_links = self.extract_pagination_links(response)
                    this_data = self.extract_data_from_response(
                        response, data_key=data_key
                    )
                    if this_data is not None:
                        if type(this_data) == list:
                            all_data += this_data
                        else:
                            all_data.append(this_data)
            except KeyError:
                pass
        else:
            return "Response from {} has no pagination links.".format(response.url)
        return all_data

    def base_request(
        self,
        method,
        uri,
        data_key=None,
        data=None,
        params=None,
        single_item=False,
        all_pages=False,
        do_not_process=False,
        no_data=False,
        poly_response=False,
        force_urlencode_data=False,
    ):
        """Base Canvas Request Method"""
        if not uri.startswith("http"):
            uri = self.instance_address + uri

        if force_urlencode_data is True:
            uri += "?" + urllib.parse.urlencode(data)
        try:
            if method == "GET":
                response = self.session.get(uri, params=params)
            elif method == "POST":
                response = self.session.post(
                    uri,
                    data=data,
                )
            elif method == "PUT":
                response = self.session.put(
                    uri,
                    data=data,
                )
            elif method == "DELETE":
                response = self.session.delete(
                    uri,
                    params=params,
                )
            else:
                response = self.session.get(
                    uri,
                    params=params,
                )

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
                return response.status_code
            if poly_response:
                r = response.json()
                if isinstance(r, list):
                    if self.has_pagination_links(response):
                        return self.depaginate(response, data_key)
                    else:
                        return self.extract_data_from_response(response, data_key)
                else:
                    return r

            return response.json()
        except requests.exceptions.HTTPError as e:
            raise CanvasAPIError(response) from e
        except requests.exceptions.Timeout as e:
            print("The request timed out.")
        except requests.exceptions.ConnectionError as e:
            print("A connection error occurred:", e)
        except requests.exceptions.RequestException as e:
            print("An error occurred:", e)

    def get(self, url, params=None, **kwargs):
        if "all_pages" in kwargs or "poly_response" in kwargs:
            max_per_page_param = {"per_page": self.max_per_page}
            combined_params = {**params, **max_per_page_param}
            return self.base_request("GET", url, params=combined_params, **kwargs)
        else:
            return self.base_request("GET", url, params=params, **kwargs)

    async def async_get(self, url, params=None, **kwargs):
        if "all_pages" in kwargs or "poly_response" in kwargs:
            max_per_page_param = {"per_page": self.max_per_page}
            combined_params = {**params, **max_per_page_param}
            return await asyncio.to_thread(
                self.base_request, "GET", url, params=combined_params, **kwargs
            )
        else:
            return await asyncio.to_thread(
                self.base_request, "GET", url, params=params, **kwargs
            )

    def post(self, url, data=None, **kwargs):
        return self.base_request("POST", url, data=data, **kwargs)

    async def async_post(self, url, data=None, **kwargs):
        return await asyncio.to_thread(
            self.base_request, "POST", url, data=data, **kwargs
        )

    def put(self, url, data=None, **kwargs):
        return self.base_request("PUT", url, data=data, **kwargs)

    async def async_put(self, url, data=None, **kwargs):
        return await asyncio.to_thread(
            self.base_request, "PUT", url, data=data, **kwargs
        )

    def delete(self, url, params=None, **kwargs):
        return self.base_request("DELETE", url, params=params, **kwargs)

    async def async_delete(self, url, params=None, **kwargs):
        return await asyncio.to_thread(
            self.base_request, "DELETE", url, params=params, **kwargs
        )


class CanvasAPIError(Exception):
    def __init__(self, response):
        self.response = response
        self.status_code = response.status_code
        self.content = response.json()

    def __str__(self):
        # Make sure the exception message shows the important details
        return f"CanvasAPIError: Status {self.status_code} - Content: {self.content}"

    def to_json(self):
        # Return a JSON representation of the error
        return json.dumps(
            {
                "status_code": self.status_code,
                "content": self.content,
            },
        )
