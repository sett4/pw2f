# -*- coding:utf-8 -*-

import gdata.photos.service
import gdata.media
import gdata.geo

import flickrapi
from elementtree.ElementTree import XML, fromstring, tostring
import urllib
import urllib2
import time

import os
import logging

from pit import Pit
from dateutil.parser import parse as parse_date

class Service(object):
    pw2f_conf = None
    def get_album_list(self):
        pass


    def get_photo_list(self, album):
        pass

    def copy_album_from(self, service, album):
        pass

    def download_or_get_filename(self, album, photo):
        if not self.pw2f_conf:
            self.pw2f_conf = Pit.get('pw2f', {'require': {'data-directory':'Photo Directory'}})

        logging.debug('photo url: '+photo._url)
        filename = os.path.basename(photo._url)
        filepath = '%s/%s/%s' % (self.pw2f_conf['data-directory'], album._title, filename)
        if os.path.exists(filepath):
            logging.debug('found in local %s' % (filepath))
            return filepath
        else:
#            logging.debug('%s is not found.' % (filepath))
            (filepath, headers) = urllib.urlretrieve(photo._url)
            logging.debug('download %s as %s' % (photo._url, filepath))
            return filepath
        pass


class Picasaweb(Service):
    def __init__(self):
        conf = Pit.get('picasaweb', {'require': {'username':'username', 'password':'password'}})
        self.gd_client = gdata.photos.service.PhotosService()
        self.gd_client.email = conf['username']
        self.gd_client.password = conf['password']
        self.gd_client.source = 'pw2f picasaweb plugin'
        self.gd_client.ProgrammaticLogin()

        self.conf = conf


    def get_album_list(self):
        albumFeed = self.gd_client.GetUserFeed(user=self.conf['username'])
        self.patch_to_albums(albumFeed.entry)
        return albumFeed.entry

    def get_photo_list(self, album):
        url = '/data/feed/api/user/%s/albumid/%s?kind=photo' % (self.conf['username'], album.gphoto_id.text)
        photoFeed = self.gd_client.GetFeed(url)
        self.patch_to_photos(photoFeed.entry)
        return photoFeed.entry


    def patch_to_albums(self, albums):
        for album in albums:
            album._published = parse_date(album.published.text)
            album._title = album.title.text


    def patch_to_photos(self, photos):
        for photo in photos:
            if not photo.title.text:
                photo._title = photo.title.text
            else:
                photo._title = ""
            if not photo.summary.text:
                photo._summary = photo.summary.text
            else:
                photo._summary = ""
            photo._url = photo.GetMediaURL()
        

    def copy_album_from(self, service, album):
        pass

class Flickr(Service):
    def __init__(self):
        conf = Pit.get('flickr', {'require': {'username':'username', 'password':'password', 'api_key':'api_key', 'secret':'secret'}})
        flickr = flickrapi.FlickrAPI(conf['api_key'], secret=conf['secret'])
        flickr.authenticate_console("write", auth_callback=None)
        self.flickr = flickr

    def copy_album_from(self, service, album):
        photos = service.get_photo_list(album)
        rsp = None
        photoset_id = None
        for photo in photos:
            filename = self.download_or_get_filename(album, photo)
            title = photo._title
            if title == None or title == "":
                title = os.path.basename(photo._url)

            # すでに無いか検索
            rsp = self.flickr.photos_search(text=title)
            self.check_and_raise(rsp)
            if len(rsp.findall('photo')) > 0:
                logging.debug('photo %s is found in flickr. skip it.' % (title))
                continue

            rsp = self.flickr.upload(filename=filename, title=title, description=photo._summary)
            self.check_and_raise(rsp)
            logging.info('upload %s', filename)

            photo_id = rsp.find('photoid').text

            # find photoset
            if not photoset_id:
                rsp = self.flickr.photosets_getList()
                self.check_and_raise(rsp)
                tmp_ids = [e.attrib['id'] for e in rsp.findall('photoset') if e.findtext('title') == album._title]
                if len(tmp_ids) > 0:
                    photoset_id = tmp_ids[0]

            # create photoset
            if not photoset_id:
                rsp = self.flickr.photosets_create(title=album._title, primary_photo_id=photo_id)
                self.check_and_raise(rsp)
                photoset_id = rsp.find('photoset').attrib['id']
                logging.info('album %s created and photo added %s. album_id:%s' % (album._title, photo_id, photoset_id))
            else:
                # add to photoset
                self.flickr.photosets_addPhoto(photoset_id=photoset_id, photo_id=photo_id)
                logging.debug('photo %s added to album %s' % (photo._url, album._title))

            time.sleep(20)

    def check_and_raise(self, rsp):
        if not rsp.attrib['stat'] == 'ok':
            err = rsp.find('err')
            raise FlickrError(u'Error: %(code)s: %(msg)s' % err.attrib)

        pass
