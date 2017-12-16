# coding=utf-8

import urllib2

def get_html_by_url(url):
    try:
        response = urllib2.urlopen(url, timeout=60)
        html = response.read().strip()
    except Exception, e:
        print("urlopen timeout", e)
        response = urllib2.urlopen(url)
        html = response.read().strip()
    return html
