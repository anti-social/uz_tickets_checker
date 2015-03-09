# coding: utf-8
import re

import execjs

import requests

# import logging
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


BASE_URL = 'http://booking.uz.gov.ua/ru/'

STATION_URL = BASE_URL + 'purchase/station/'

SEARCH_URL = BASE_URL + 'purchase/search/'

BASE_HEADERS = {
    'Connection': 'keep-alive',
    'Host': 'booking.uz.gov.ua',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0',
}

SEARCH_HEADERS = {
    'GV-Ajax': 1,
    'GV-Referer': BASE_URL,
    'GV-Screen': '1366x768',
    'GV-Unique-Host': 1,
    'Origin': 'http://booking.uz.gov.ua',
    'Referer': BASE_URL,
}

TOKEN_RE = re.compile('({}.*{})'.format(re.escape('$$_='), re.escape(')())();')))


def get_cookies_and_token():
    url = BASE_URL
    headers = BASE_HEADERS
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return
    matches = TOKEN_RE.findall(resp.text)
    if not matches:
        return
    if len(matches) > 1:
        return
    js_obfuscated = matches[0]
    js_fake_storage = 'localStorage = {token: undefined, setItem: function (key, value) {this.token = value}}'
    js_code = (
        'function getToken() {{\n'
        '\t{};\n'
        '\t{};\n'
        '\treturn localStorage.token;\n'
        '}}'
    ).format(js_fake_storage, js_obfuscated)
    return resp.cookies, execjs.compile(js_code).call('getToken')


def find_station(name, cookies):
    name = name.lower()
    url = STATION_URL + name[:2]
    resp = requests.post(url, cookies=cookies)
    if resp.status_code != 200:
        return
    stations = resp.json()['value']
    for station in stations:
        if station['title'].lower() == name:
            return station['station_id']


def get_trains(from_station_id, from_station_name, to_station_id, to_station_name, dep_date, cookies, token):
    data = {
        'station_id_from': from_station_id,
        'station_id_till': to_station_id,
        'station_from': from_station_name,
        'station_till': to_station_name,
        'date_dep': dep_date,
        'time_dep': '00:00',
        'time_dep_till': '',
        'another_ec': 0,
        'search': '',
    }
    headers = dict(BASE_HEADERS, **SEARCH_HEADERS)
    headers['GV-Token'] = token
    resp = requests.post(SEARCH_URL, data, headers=headers, cookies=cookies)
    if resp.status_code != 200:
        return

    return resp.json()['value']


def format_trains(data):
    rows = []
    if isinstance(data, list):
        for train in data:
            rows.append(u'{0[num]} {0[from][src_date]} - {0[till][src_date]}'.format(train))
            for place_type in train['types']:
                rows.append(u'\t{0[letter]}: {0[places]}'.format(place_type))
    else:
        rows.append(data)
    return '\n'.join(rows)


def find_tickets(from_station_name, to_station_name, dep_date):
    cookies, token = get_cookies_and_token()
    from_station_id = find_station(from_station_name, cookies)
    if not from_station_id:
        print u"Cannot find station: '{}'".format(from_station_name)
    to_station_id = find_station(to_station_name, cookies)
    if not to_station_id:
        print u"Cannot find station: '{}'".format(to_station_name)
    trains_data = get_trains(from_station_id, from_station_name, to_station_id, to_station_name, dep_date, cookies, token)
    print format_trains(trains_data)
