# Canopy


A helper library for the Instructure Canvas API base on the basic request handling of Py3Canvas and modified API spec files

## Usage

In your project create two folders: `specs` and `apis`. These will contain the API spec files downloaded from Canvas live documentation which has the openAPI spec files, and the generated API files used for making API calls. Install canopy by running `pip install -e git+https://github.com/tylerclair/canopy.git#egg=canopy`

You can use the canvas_api_builder script to download the spec files, generate the Canvas API modules in both synchronous and asynchronous versions, and generate the canvas client file that you can use in your own projects. You can use this directly in your project or you can generate them in a separate project, install Canopy, and then move the apis folder and canvas client to your own project if desired.

### Updating spec files

```
$ canvas_api_builder update-spec-files --specs-folder specs/
Updated specs/api_token_scopes.json
Updated specs/account_domain_lookups.json
Updated specs/account_notifications.json
Updated specs/account_reports.json
Updated specs/accounts.json
Updated specs/accounts_(lti).json
Updated specs/admins.json
Updated specs/analytics.json
...
```
For more information on using this command  run `$ canvas_api_builder update-spec-files --help`

### Build API from spec file

**Synchronous**
```
$ canvas_api_builder build-api-from-specfile --specfile specs/accounts.json --output-folder apis/
Generating code for specfile: accounts.json
```
**Asynchronous**
```
$ canvas_api_builder build-api-from-specfile --specfile specs/accounts.json --output-folder apis/ --generate-async
Generating async code for specfile: accounts.json
```

**Note: The API modules are generated using a template. Make sure the code is valid before using it.**

For more information on using this command  run `$ canvas_api_builder build-api-from-specfile --help`

### Build Canvas client file
```
$ canvas_api_builder build-canvas-client-file --apis-folder apis/
Generating canvas_client.py file
```

### Build all APIs
**Note: It is generally not recommended to generate all the APIs at this time**. There are many API endpoints that have issues that will cause the loading of the client to fail. Only after you correct *all* the issues within the API files will the client load without issues.

```
$ canvas_api_builder build-all-apis --specs-folder specs/ --output-folder apis/
Generating code for specfile: api_token_scopes.json
Generating code for specfile: account_domain_lookups.json
Generating code for specfile: account_notifications.json
Generating code for specfile: account_reports.json
Generating code for specfile: accounts.json
Generating code for specfile: accounts_(lti).json
Generating code for specfile: admins.json
Generating code for specfile: analytics.json
...
```
For more information on using this command  run `$ canvas_api_builder build-all-apis --help`


## Manually testing canvas_api_builder commands

You can use the Python REPL to run the builder commands manually. I suggest creating separate test folders for your apis, spec files, and canvas client files. Open the Python REPL by entering `python` in a shell from the root of the package.

import the specific command from the `canvas_api_builder.py` file.
```
>>> from canopy.scripts.canvas_api_builder import build_api_from_specfile
>>> build_api_from_specfile.main(["-s", "tests/specs/sections.json", "-o", "tests/apis"])
Generating code for specfile: sections.json
```
Once a command is ran it will exit the REPL and you will have to launch it again and repeat the process for additional commands. In the future I may create a test file for the commands, but for now any changes can be tested using this manual method.

## Usage in your project

```python
from canvas_client import CanvasClient

canvas_url = "https://abc.instructure.com"
token = "your_token_here"

client = CanvasClient(canvas_url, token, max_per_page=100)
user_profile = client.users.get_user_profile("self")
print(user_profile)
```
## Asynchronous usage in your project
Canopy now has the ability to perform asynchronous API calls, this is very different from the traditional usage. There are still some calls that will be blocking due to them relying on the returned result of the previous API call, i.e. paginated requests. Despite this drawback there is still a vast improvement in performance especially when you have to make a large amount of requests that do not rely on other calls responses.

Here is an example of how we can take a list of student IDs and return their names:

```python
import asyncio
from canvas_client import CanvasClient
from time import perf_counter

canvas_url = "https://abc.instructure.com"
token = "your_token_here"

client = CanvasClient(canvas_url, token, max_per_page=100)

# Abbreviated for space
student_ids = [
    "123",
    "456",
    "789",
]


# asynchronous
async def get_user_details_async(student_id):
    user_details_async = await client.users_async.show_user_details(
        id=student_id
    )
    return user_details_async["name"]


# synchronous
def get_user_details(student_id):
    user_details = client.users.show_user_details(id=student_id)
    return user_details["name"]


async def main():
    # synchronous
    time_before = perf_counter()
    for student_id in student_ids:
        result = get_user_details(student_id)
        print(result)
    print(f"Total time (synchronous): {perf_counter() - time_before}")

    # asynchronous
    time_before = perf_counter()
    tasks = [get_user_details_async(student_id) for student_id in student_ids]
    results = await asyncio.gather(*tasks)
    print(results)
    print(f"Total time (asynchronous): {perf_counter() - time_before}")

    # asynchronous print as completed
    time_before = perf_counter()
    tasks = [get_user_details_async(student_id) for student_id in student_ids]
    for coro in asyncio.as_completed(tasks):
        name = await coro
        print(name["name"])
    print(
        f"Total time (asynchronous print as completed): {perf_counter() - time_before}"
    )

asyncio.run(main())
```

This is the results of the above performance test with a list of 50 student IDs:
```bash
# Results removed for space
Total time (synchronous): 9.39928955299547
# Results removed for space
Total time (asynchronous): 1.3862317899911432
# Results removed for space
Total time (asynchronous print as completed): 0.9531320789974416
```

Now with 295 students:
```bash
Total time (synchronous): 50.22708906700427
Total time (asynchronous): 5.239625043002889
Total time (asynchronous print as completed): 4.629659270998673
```

