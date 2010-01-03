#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')

from pit import Pit
from dateutil.parser import parse as parse_date
import service


def main():
    conf = Pit.get('pw2f', {'require':{'last-time':'yyyy-mm-dd hh:mm:ss+hh:mm'}})
    flickr = service.Flickr()
    picasaweb = service.Picasaweb()
    for album in reversed(picasaweb.get_album_list()):
        logging.info('title: %s, published: %s' % (album._title,
                                            album._published))
        if not album._title == '2009-12-29_天狗-硫黄' \
                and album._published > parse_date(conf['last-time']):
            flickr.copy_album_from(picasaweb, album)
        else:
            logging.debug('skip album %s: published:%s' % (album._title, album._published))
#        Pit.set('pw2f', {'last-time':album._published})



if __name__ == '__main__':
    main();
