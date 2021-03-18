import functools
from flask import Flask, abort, request, jsonify


# JSON schema validator
def json_endpoint(func):
    @functools.wraps(func)
    def _json_endpoint(*args, **kwargs):
        # Make sure a JSON request came in
        if not isinstance(request.json, dict):
            print("Request was not valid JSON")
            abort(400)
        # Make sure each required field is present
        arguments = {}
        for key, value in func.__annotations__.items():
            if not isinstance(request.json.get(key, None), value):
                print(f'Request does not have JSON parameter "{key}" of type "{value.__name__}"')
                abort(400)
            arguments[key] = request.json[key]
        # Call the original function
        result = func(*args, **arguments, **kwargs)
        # If an integer is returned as the second value,
        # use that as the return code.
        if isinstance(result, (tuple, list)) and len(result) == 2:
            result, status_code = result
            response = jsonify(result)
            response.status_code = status_code
        else:
            response = jsonify(result)
        # Return the modified response
        return response
    return _json_endpoint


class JsonFlask(Flask):
    def json_route(self, *args, **kwargs):
        _route = self.route(*args, methods=['POST'], **kwargs)
        def _json_route(func):
            return _route(json_endpoint(func))
        return _json_route