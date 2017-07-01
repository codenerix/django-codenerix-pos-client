# Webserver libraries
from werkzeug.wrappers import Request
from werkzeug.exceptions import HTTPException, NotFound

from codenerix.lib.debugger import Debugger

class WebServer(Debugger):
    
    def __init__(self):
        self.set_name('WebServer')
        self.set_debug()
    
    def dispatch(self, request):
        # self.debug("Dispatch")
        # Map and match URLs
        adapter = self.urls.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
        except HTTPException as e:
            return e
        
        # Make decisions
        method = getattr(self, endpoint, None)
        if method:
            return method(request)
        else:
            raise NotFound("Not found!")
    
    def wsgi_app(self, environ, start_response):
        # self.debug("WSGI_APP")
        # Get request
        request = Request(environ)
        # Send to dispatch
        response = self.dispatch(request)
        # Return response
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        '''
        # Entry point
        '''
        # self.debug("CALL")
        return self.wsgi_app(environ, start_response)

