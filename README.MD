Canopy
======

A helper library for the Instructure Canvas API base on the basic request handling of Py3Canvas and modified API spec files

Usage
------

**canvas_client.py**
```python
    from apis.users import UsersAPI
    from canopy import CanvasSession

class CanvasClient(object):
    def __init__(self, instance_address, access_token, max_per_page):
        self.instance_address = instance_address
        self.access_token = access_token
        self.max_per_page = max_per_page
        self.client = CanvasSession(
            self.instance_address, self.access_token, self.max_per_page
        )
        self.users = UsersAPI(self.client)
```

**my_app.py**
```python
    from canvas_client import CanvasClient
    import os

    ACCESS_TOKEN = os.environ.get("CANVAS_TOKEN", None)
    URL_INSTANCE = os.environ.get("PY3CANVAS_URL", None)
    client = CanvasClient(URL_INSTANCE, ACCESS_TOKEN, max_per_page=100)

    user_profile = client.users.get_user_profile("self")
    print(user_profile)
```

API Builder
-----------
The builder script will allow you to take the Canvas API Swagger JSON files and generate the API modules.