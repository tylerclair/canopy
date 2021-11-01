# Canopy


A helper library for the Instructure Canvas API base on the basic request handling of Py3Canvas and modified API spec files

## Usage

In your project create two folders: `specs` and `apis`. These will contain the API spec files downloaded from Canvas live documentation which has the openAPI spec files, and the generated API files used for making API calls. Install canopy by running `pip install git+https://github.com/tylerclair/canopy.git`

You can now use the canvas_api_builer script to download the spec files, generate the Canvas API modules, and generate the canvas client file that you can use in your own projects. You can use this directly in your project or you can generate them in a seperate project, install canopy, and then move the apis folder and canvas client to your own project if desired.

### Updating spec files

```
$ canvas_api_builder update-spec-files --specfile-path specs/
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

```
$ canvas_api_builder build-api-from-specfile --specfile accounts.json --output-folder apis/
Generating code for specfile: accounts.json
```
For more information on using this command  run `$ canvas_api_builder build-api-from-specfile --help`

### Build Canvas client file
```
$ canvas_api_builder build-canvas-client-file --apifolder-path apis/
Generating canvas_client.py file
```

### Build all APIs
**Note: It is generally not recommended to generate all the APIs at this time**. There are many API endpoints that have issues that will cause the loading of the client to fail. Only after you correct *all* the issues within the API files will the client load without issues.

```
$ canvas_api_builder build-all-apis --specfile-path specs/ --output-folder apis/
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