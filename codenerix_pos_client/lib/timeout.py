#########################################################################
#                                                                       #
# Name:      TIMEOUT                                                    #
#                                                                       #
# Project:   Likindoy                                                   #
# Module:    Common                                                     #
# Started:   2007060500                                                 #
#                                                                       #
# Important: WHEN EDITING THIS FILE, USE SPACES TO INDENT - NOT TABS!   #
#                                                                       #
#########################################################################
#                                                                       #
# Juan Miguel Taboada Godoy <juanmi@likindoy.org>                       #
#                                                                       #
# This file is part of Likindoy.                                        #
#                                                                       #
# Likindoy is free software: you can redistribute it and/or modify      #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 2 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# Likindoy is distributed in the hope that it will be useful,           #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
# GNU General Public License for more details.                          #
# You should have received a copy of the GNU General Public License     #
# along with Likindoy.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                       #
#########################################################################
'''
Timeout exception definition and timeout function to allow the user to call
functions under specific timeout. The function will raise and exception when
timeout is reached if the called function didn't finish execution before
'''

__version__ = "2009101500"

import signal

__all__ = [ "TimedOutException" , "timeout" ]

class TimedOutException(Exception):
    '''
    Timeout exception definition
    '''

    def __init__(self, value = "Timed Out"):
        '''
        Parameters:
        - `value`: text to raise in the exception
        '''
        self.value = value

    def __str__(self):
        return repr(self.value)


def timeout(f, timeout, *args, **kwargs):
    '''
    Function that controls the timeout

    Parameters:
    - `f`: function to process under timeout control
    - `timeout`: total number of seconds to wait until timeout (not allowed 0
      or less)
    - `args` & `kwargs`: to allow in this function any kind of parameters
       to be passed to function f

    Exceptions:
    - `IOError`: parameter error
    - `TimedOutException`: when timeout reach to the limit and the function is
       still executing
    '''

    # Control that timeout can not be zero or negative
    if timeout <= 0:
        raise IOError("Timeout can not be zero or less than zero")

    # Define the handler
    def handler(signum, frame):
        raise TimedOutException()

    # Remember the actual signal handler
    old = signal.signal(signal.SIGALRM, handler)

    # Install timeout control
    signal.alarm(timeout)

    try:
        # Launch the function with all arguments
        result = f(*args, **kwargs)
    finally:
        # Restore old signal handler
        signal.signal(signal.SIGALRM, old)

    # Remove timeout control
    signal.alarm(0)

    # Return the result of the function
    return result

