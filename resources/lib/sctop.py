import datetime
import time
import urllib
import urllib2
import util
import xbmc
import sys
import json
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcutil

__scriptid__ = 'plugin.video.stream-cinema'
__scriptname__ = 'stream-cinema.online'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__set__ = __addon__.getSetting
__language__ = __addon__.getLocalizedString

BASE_URL="http://stream-cinema.online/kodi"
API_VERSION="1.2"
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
player = None
uid = None
traktlistlast = None
submiturl = 'http://movies.bbaron.sk/plugin/submit/'

addon = xbmcaddon.Addon

dialog = xbmcgui.Dialog()

progressDialog = xbmcgui.DialogProgress()

keyboard = xbmc.Keyboard

infoLabel = xbmc.getInfoLabel

addonInfo = addon().getAddonInfo

execute = xbmc.executebuiltin

trCL = 'bb21f3665cf0fa07f2a1a420ec6990317c49dee91af8e012cb836d66674e75c4'
trSC = 'fcc25d240d560326147cfb32fc0554868333dc954dc150ea2519f0a2a259f6e2'

def getSetting(setting):
    return __addon__.getSetting(setting).strip().decode('utf-8')

def setSetting(setting, value):
    __addon__.setSetting(setting, str(value))

def getSettingAsBool(setting):
    return getSetting(setting).lower() == "true"

def getSettingAsFloat(setting):
    try:
        return float(getSetting(setting))
    except ValueError:
        return 0

def getSettingAsInt(setting):
    try:
        return int(getSettingAsFloat(setting))
    except ValueError:
        return 0

def getString(string_id):
    return __addon__.getLocalizedString(string_id).encode('utf-8', 'ignore')

def notification(header, message, time=5000, icon=__addon__.getAddonInfo('icon')):
    xbmc.executebuiltin("XBMC.Notification(%s,%s,%i,%s)" % (header, message, time, icon))

def yesnoDialog(line1, line2, line3, heading=addonInfo('name'), nolabel='', yeslabel=''):
    return dialog.yesno(heading, line1, line2, line3, nolabel, yeslabel)

def selectDialog(list, heading=addonInfo('name')):
    return dialog.select(heading, list)

def infoDialog(message, heading=addonInfo('name'), icon='', time=3000, sound=False):
    if icon == '': icon = icon=__addon__.getAddonInfo('icon')
    elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
    elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
    elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
    dialog.notification(heading, message, icon, time, sound=sound)

def openSettings(query=None, id=addonInfo('id')):
    try:
        idle()
        execute('Addon.OpenSettings(%s)' % id)
        if query == None: raise Exception()
        c, f = query.split('.')
        execute('SetFocus(%i)' % (int(c) + 100))
        execute('SetFocus(%i)' % (int(f) + 200))
    except:
        return

def idle():
    return execute('Dialog.Close(busydialog)')

def getMediaType():
    if xbmc.getCondVisibility('Container.Content(tvshows)'):
        return "show"
    elif xbmc.getCondVisibility('Container.Content(seasons)'):
        return "season"
    elif xbmc.getCondVisibility('Container.Content(episodes)'):
        return "episode"
    elif xbmc.getCondVisibility('Container.Content(movies)'):
        return "movie"
    else:
        return None

def sleep(sleep_time):
    while not xbmc.abortRequested and sleep_time > 0:
        sleep_time -= 100
        xbmc.sleep(99)

def iso_2_utc(iso_ts):
    if not iso_ts or iso_ts is None: return 0
    delim = -1
    if not iso_ts.endswith('Z'):
        delim = iso_ts.rfind('+')
        if delim == -1: delim = iso_ts.rfind('-')

    if delim > -1:
        ts = iso_ts[:delim]
        sign = iso_ts[delim]
        tz = iso_ts[delim + 1:]
    else:
        ts = iso_ts
        tz = None

    if ts.find('.') > -1:
        ts = ts[:ts.find('.')]

    try: d = datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
    except TypeError: d = datetime.datetime(*(time.strptime(ts, '%Y-%m-%dT%H:%M:%S')[0:6]))

    dif = datetime.timedelta()
    if tz:
        hours, minutes = tz.split(':')
        hours = int(hours)
        minutes = int(minutes)
        if sign == '-':
            hours = -hours
            minutes = -minutes
        dif = datetime.timedelta(minutes=minutes, hours=hours)
    utc_dt = d - dif
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = utc_dt - epoch
    try: seconds = delta.total_seconds()  # works only on 2.7
    except: seconds = delta.seconds + delta.days * 24 * 3600  # close enough
    return seconds

def request(url, headers={}, output="content"):
    util.debug('request: %s' % url)
    req = urllib2.Request(url, headers=headers)
    req.add_header('User-Agent', util.UA)
    if util._cookie_jar is not None:
        util._cookie_jar.add_cookie_header(req)
    data = ''
    try:
        response = urllib2.urlopen(req)
        while True:
            try:
                tmp = response.read()
            except http.client.IncompleteRead as icread:
                data = data + icread.partial.decode('utf-8')
                continue
            else:
                data = data + tmp.decode('utf-8')
                break
        code = response.code
        info = response.info()
        response.close()
    except urllib2.HTTPError, error:
        code = error.code
        data = util._solve_http_errors(url, error)
        info = None
    util.debug('len(data) %s' % len(data))
    
    if (output == "content"):
        return data
    if (output == "info"):
        return (data, code, info)
    else:
        return (data, code)


def post(url, data, headers={}, output="content"):
    postdata = urllib.urlencode(data)
    req = urllib2.Request(url, postdata, headers)
    req.add_header('User-Agent', util.UA)
    util.debug("[SC] post: %s" % url )
    if util._cookie_jar is not None:
        util._cookie_jar.add_cookie_header(req)
    try:
        response = urllib2.urlopen(req)
        data = response.read()
        code = response.code
        response.close()
    except urllib2.HTTPError, error:
        data = util._solve_http_errors(url, error)
        code = error.code

    if (output == "content"):
        return data
    else:
        return (data, code)


def post_json(url, data, headers={}, output="content"):
    postdata = json.dumps(data)
    headers['Content-Type'] = 'application/json'
    req = urllib2.Request(url, postdata, headers)
    req.add_header('User-Agent', util.UA)
    if util._cookie_jar is not None:
        util._cookie_jar.add_cookie_header(req)
    try:
        response = urllib2.urlopen(req)
        data = response.read()
        code = response.code
        response.close()
    except urllib2.HTTPError, error:
        data = util._solve_http_errors(url, error)
        code = error.code

    if (output == "content"):
        return data
    else:
        return (data, code)

def _create_plugin_url(params, plugin=sys.argv[0]):
    url = []
    for key in params.keys():
        # "menu", "img", "type", "size", "title"]:
        if key not in ["dtitle", "url", "action", "list", "cmd", "down", "play", "force",
                        "search-list", "search", "search-remove", "search-edit", "tl",
                        "id", "subtype", "title", "name", "imdb", "tvdb", "content"]:
            continue
        value = str(params[key])
        value = value.encode('utf-8')
        if value.encode('hex') != "": 
            url.append(key + '=' + value.encode('hex',) + '&')
    return plugin + '?' + ''.join(url)

def merge_dicts(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

def getCondVisibility(text):
    '''executes the builtin getCondVisibility'''
    # temporary solution: check if strings needs to be adjusted for backwards compatability
    if KODI_VERSION < 17:
        text = text.replace("Integer.IsGreater", "IntegerGreaterThan")
        text = text.replace("String.Contains", "SubString")
        text = text.replace("String.IsEqual", "StringCompare")
    return xbmc.getCondVisibility(text)

try:
    from storagecache import StorageCache
    cache = StorageCache()
except Exception, e:
    util.debug("[SC] error cache: %s" % str(e) )
    try:
        import StorageServer
        cache = StorageServer.StorageServer(__scriptname__)
    except:
        import storageserverdummy as StorageServer
        cache = StorageServer.StorageServer(__scriptname__)

(v1, v2, v3) = str(xbmcplugin.__version__).split('.')
if int(v1) == 2 and int(v2) <= 20:
    xbmcplugin.SORT_METHOD_VIDEO_USER_RATING = 20

# lebo medved na 4 je maco
sortmethod = {
    14:	xbmcplugin.SORT_METHOD_ALBUM,
    15:	xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE,
    11:	xbmcplugin.SORT_METHOD_ARTIST,
    13:	xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE,
    42:	xbmcplugin.SORT_METHOD_BITRATE,
    40:	xbmcplugin.SORT_METHOD_CHANNEL,
    17:	xbmcplugin.SORT_METHOD_COUNTRY,
    3:	xbmcplugin.SORT_METHOD_DATE,
    21:	xbmcplugin.SORT_METHOD_DATEADDED,
    43:	xbmcplugin.SORT_METHOD_DATE_TAKEN,
    6:	xbmcplugin.SORT_METHOD_DRIVE_TYPE,
    8:	xbmcplugin.SORT_METHOD_DURATION,
    24:	xbmcplugin.SORT_METHOD_EPISODE,
    5:	xbmcplugin.SORT_METHOD_FILE,
    34:	xbmcplugin.SORT_METHOD_FULLPATH,
    16:	xbmcplugin.SORT_METHOD_GENRE,
    1:	xbmcplugin.SORT_METHOD_LABEL,
    35:	xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS,
    2:	xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,
    36:	xbmcplugin.SORT_METHOD_LASTPLAYED,
    38:	xbmcplugin.SORT_METHOD_LISTENERS,
    30:	xbmcplugin.SORT_METHOD_MPAA_RATING,
    0:	xbmcplugin.SORT_METHOD_NONE,
    37:	xbmcplugin.SORT_METHOD_PLAYCOUNT,
    23:	xbmcplugin.SORT_METHOD_PLAYLIST_ORDER,
    28:	xbmcplugin.SORT_METHOD_PRODUCTIONCODE,
    22:	xbmcplugin.SORT_METHOD_PROGRAM_COUNT,
    4:	xbmcplugin.SORT_METHOD_SIZE,
    29:	xbmcplugin.SORT_METHOD_SONG_RATING,
    32:	xbmcplugin.SORT_METHOD_STUDIO,
    33:	xbmcplugin.SORT_METHOD_STUDIO_IGNORE_THE,
    9:	xbmcplugin.SORT_METHOD_TITLE,
    10:	xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE,
    7:	xbmcplugin.SORT_METHOD_TRACKNUM,
    39:	xbmcplugin.SORT_METHOD_UNSORTED,
    19:	xbmcplugin.SORT_METHOD_VIDEO_RATING,
    31:	xbmcplugin.SORT_METHOD_VIDEO_RUNTIME,
    26:	xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE,
    27:	xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE,
    25:	xbmcplugin.SORT_METHOD_VIDEO_TITLE,
    20:	xbmcplugin.SORT_METHOD_VIDEO_USER_RATING,
    18:	xbmcplugin.SORT_METHOD_VIDEO_YEAR
}

ALL_VIEW_CODES={
    'list': {
        'skin.estuary': 50, # List
        'skin.confluence': 50, # List
        'skin.aeon.nox': 50, # List
        'skin.droid': 50, # List
        'skin.quartz': 50, # List
        'skin.re-touched': 50, # List
    },
    'thumbnail': {
        'skin.estuary': 500, # Thumbnail
        'skin.confluence': 500, # Thumbnail
        'skin.aeon.nox': 500, # Wall
        'skin.droid': 51, # Big icons
        'skin.quartz': 51, # Big icons
        'skin.re-touched': 500, #Thumbnail
    },
    'movies': {
        'skin.estuary': 500,
        'skin.confluence': 500, # Thumbnail 515, # Media Info 3
        'skin.aeon.nox': 500, # Wall
        'skin.droid': 51, # Big icons
        'skin.quartz': 52, # Media info
        'skin.re-touched': 500, #Thumbnail
    },
    'tvshows': {
        'skin.estuary': 501, # Banner
        'skin.confluence': 505, # Banner 505, Thumbnail 515, # Media Info 3
        'skin.aeon.nox': 500, # Wall
        'skin.droid': 51, # Big icons
        'skin.quartz': 52, # Media info
        'skin.re-touched': 500, #Thumbnail
    },
    'seasons': {
        'skin.estuary': 50, # List
        'skin.confluence': 50, # List
        'skin.aeon.nox': 50, # List
        'skin.droid': 50, # List
        'skin.quartz': 52, # Media info
        'skin.re-touched': 50, # List
    },
    'episodes': {
        'skin.estuary': 54, # Media Info
        'skin.confluence': 504, # Media Info
        'skin.aeon.nox': 518, # Infopanel
        'skin.droid': 50, # List
        'skin.quartz': 52, # Media info
        'skin.re-touched': 550, # Wide
    },
}
