Canopy
======

A helper library for the Instructure Canvas API base on the basic request handling of Py3Canvas.

Usage
------

    from canopy import CanvasClient

    client = CanvasClient('https://abc.instructure.com', 'access token')
    user = client.base_request('GET', '/api/v1/users/self/profile')
    print(user)
