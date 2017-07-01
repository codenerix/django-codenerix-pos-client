# -*- coding: utf-8 -*-
#
# django-codenerix-pos-client
#
# Copyright 2017 Juanmi Taboada - http://www.juanmitaboada.com
#
# Project URL : http://www.codenerix.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

