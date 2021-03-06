from gevent import monkey
monkey.patch_all()
import gevent.socket

from youtube import yt_app
from youtube import util

# these are just so the files get run - they import yt_app and add routes to it
from youtube import watch, search, playlist, channel, local_playlist, comments, post_comment, subscriptions

import settings

from gevent.pywsgi import WSGIServer
import urllib
import urllib3
import socket
import socks, sockshandler
import subprocess
import re




def youtu_be(env, start_response):
    id = env['PATH_INFO'][1:]
    env['PATH_INFO'] = '/watch'
    if not env['QUERY_STRING']:
        env['QUERY_STRING'] = 'v=' + id
    else:
        env['QUERY_STRING'] += '&v=' + id
    yield from yt_app(env, start_response)

def proxy_site(env, start_response):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)',
        'Accept': '*/*',
    }
    url = "https://" + env['SERVER_NAME'] + env['PATH_INFO']
    if env['QUERY_STRING']:
        url += '?' + env['QUERY_STRING']


    content, response = util.fetch_url(url, headers, return_response=True)

    headers = response.getheaders()
    if isinstance(headers, urllib3._collections.HTTPHeaderDict):
        headers = headers.items()

    start_response('200 OK', headers )
    yield content

site_handlers = {
    'youtube.com':yt_app,
    'youtu.be':youtu_be,
    'ytimg.com': proxy_site,
    'yt3.ggpht.com': proxy_site,
    'lh3.googleusercontent.com': proxy_site,

}

def split_url(url):
    ''' Split https://sub.example.com/foo/bar.html into ('sub.example.com', '/foo/bar.html')'''
    # XXX: Is this regex safe from REDOS?
    # python STILL doesn't have a proper regular expression engine like grep uses built in...
    match = re.match(r'(?:https?://)?([\w-]+(?:\.[\w-]+)+?)(/.*|$)', url)
    if match is None:
        raise ValueError('Invalid or unsupported url: ' + url)
    
    return match.group(1), match.group(2)
    


def error_code(code, start_response):
    start_response(code, ())
    return code.encode()

def site_dispatch(env, start_response):
    client_address = env['REMOTE_ADDR']
    try:
        # correct malformed query string with ? separators instead of &
        env['QUERY_STRING'] = env['QUERY_STRING'].replace('?', '&')

        method = env['REQUEST_METHOD']
        path = env['PATH_INFO']

        if method=="POST" and client_address not in ('127.0.0.1', '::1'):
            yield error_code('403 Forbidden', start_response)
            return

        # redirect localhost:8080 to localhost:8080/https://youtube.com
        if path == '' or path == '/':
            start_response('302 Found', [('Location', '/https://youtube.com')])
            return

        try:
            env['SERVER_NAME'], env['PATH_INFO'] = split_url(path[1:])
        except ValueError:
            yield error_code('404 Not Found', start_response)
            return

        base_name = ''
        for domain in reversed(env['SERVER_NAME'].split('.')):
            if base_name == '':
                base_name = domain
            else:
                base_name = domain + '.' + base_name

            try:
                handler = site_handlers[base_name]
            except KeyError:
                continue
            else:
                yield from handler(env, start_response)
                break
        else:   # did not break
            yield error_code('404 Not Found', start_response)
            return
    except Exception:
        start_response('500 Internal Server Error', ())
        yield b'500 Internal Server Error'
        raise
    return





if settings.allow_foreign_addresses:
    server = WSGIServer(('0.0.0.0', settings.port_number), site_dispatch)
else:
    server = WSGIServer(('127.0.0.1', settings.port_number), site_dispatch)
print('Started httpserver on port ' , settings.port_number)
server.serve_forever()
