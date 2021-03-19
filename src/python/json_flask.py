import functools
import inspect
from inspect import Signature, Parameter
from flask import Flask, abort, request, jsonify
from cache import Cache


class JsonFlask(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.authtoken_cache = Cache()
        
    def json_route(self, *args, **kwargs):
        route_decorator = self.route(*args, methods=['POST'], **kwargs)
        json_decorator = json_endpoint(self)
        def json_route_decorator(func):
            return route_decorator(json_decorator(func))
        return json_route_decorator


class UserId:
    @staticmethod
    def validate_json(app):
        user_id = app.authtoken_cache[request.json.get('authtoken', None)]
        if user_id is None:
            response = jsonify({
                "error": "missing or expired token, login required"
            })
            response.status_code = 401
            abort(response)
        return user_id            


# JSON schema validator
def json_endpoint(app: JsonFlask):
    def json_decorator(func):
        @functools.wraps(func)
        def _json_decorator():
            # Make sure a JSON request came in
            if not isinstance(request.json, dict):
                response = jsonify({
                    "error": "request was not valid JSON"
                })
                response.status_code = 400
                abort(response)
            # Make sure each field is present
            parameters = inspect.signature(func, follow_wrapped=True).parameters
            args = []
            kwargs = {}
            for parameter in parameters.values():
                # If the type has a "validate_json" function, call that
                if hasattr(parameter.annotation, 'validate_json'):
                    arg_value = parameter.annotation.validate_json(app)
                # Otherwise, if the type has an annotation, make sure it matches
                elif parameter.annotation is not Parameter.empty:
                    arg_value = request.json.get(parameter.name, None)
                    if not isinstance(arg_value, parameter.annotation):
                        response = jsonify({
                            "error": f'incorrect type for JSON parameter "{parameter.name}": "{type(arg_value).__name__}"'
                        })
                        response.status_code = 400
                        abort(response)
                # Finally, if no validate_json() and no annotation, just ignore this parameter
                else:
                    continue
                # Add argument to argument data structures
                if parameter.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
                    args.append(arg_value)
                elif parameter.kind is Parameter.KEYWORD_ONLY:
                    kwargs[parameter.name] = arg_value
            # Call the original function
            result = func(*args, **kwargs)
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
        return _json_decorator
    return json_decorator