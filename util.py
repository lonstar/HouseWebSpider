# coding=utf-8

import urllib.request

def get_html_by_url(url):
    try:
        response = urllib.request.urlopen(url, timeout=60)
        html = response.read().strip()
    except Exception as e:
        print("urlopen timeout", e)
        response = urllib2.urlopen(url)
        html = response.read().strip()
    return html
