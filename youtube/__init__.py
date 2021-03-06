from youtube import util
import flask
import settings
import traceback
from sys import exc_info
yt_app = flask.Flask(__name__)
yt_app.url_map.strict_slashes = False


yt_app.add_url_rule('/settings', 'settings_page', settings.settings_page, methods=['POST', 'GET'])

@yt_app.route('/')
def homepage():
    return flask.render_template('home.html', title="Youtube local")


theme_names = {
    0: 'light_theme',
    1: 'gray_theme',
    2: 'dark_theme',
}

@yt_app.context_processor
def inject_theme_preference():
    return {
        'theme_path': '/youtube.com/static/' + theme_names[settings.theme] + '.css',
    }

@yt_app.template_filter('commatize')
def commatize(num):
    if num is None:
        return ''
    if isinstance(num, str):
        num = int(num)
    return '{:,}'.format(num)

@yt_app.errorhandler(500)
def error_page(e):
    if (exc_info()[0] == util.FetchError
        and exc_info()[1].code == '429'
        and settings.route_tor
    ):
        error_message = ('Error: Youtube blocked the request because the Tor'
            ' exit node is overutilized. Try getting a new exit node by'
            ' using the New Identity button in the Tor Browser.')
        if exc_info()[1].ip:
            error_message += ' Exit node IP address: ' + exc_info()[1].ip
        return flask.render_template('error.html', error_message=error_message), 502
    return flask.render_template('error.html', traceback=traceback.format_exc()), 500
