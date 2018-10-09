# -*- coding: utf-8 -*-
import codecs
import os
import re

import simplejson
from abc import abstractmethod

from lxml import etree
from urllib import request, error
import gzip


class ParserBase(object):
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
        'Content-Type': 'text/html;charset=UTF-8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Accept-Encoding': 'gzip, deflate'
    }
    _target_dic = {}
    _target_set = set()
    _log_target_set = set()
    _state_dic = {}

    _current_page = 0
    _sum_page = 0
    _current_title = 0
    _sum_title = 0
    _current_image = 0
    _sum_image = 0

    @abstractmethod
    def get_home_page(self):
        pass

    @abstractmethod
    def get_output_path(self):
        pass

    def get_html_content(self, url, on_error=None, encoding='utf-8'):
        req = request.Request(url=url, headers=self._headers)
        try:
            page = request.urlopen(req)
            data = page.read()
            if page.getheader(name='Content-Encoding') == 'gzip':
                data = gzip.decompress(data)
            if encoding is not None:
                data = data.decode(encoding)
            return data
        except error.HTTPError as e:
            if on_error is not None:
                on_error(e)
        return None

    def download_file(self, url, on_error=None):
        return self.get_html_content(url, on_error=on_error, encoding=None)

    @staticmethod
    def get_etree_html(self, url, encoding='utf-8'):
        content = self.get_html_content(url, encoding=encoding)
        return etree.HTML(content)

    @abstractmethod
    def get_page_url(self, idx):
        pass

    @abstractmethod
    def get_page_number(self):
        pass

    @abstractmethod
    def get_target_list(self):
        pass

    @abstractmethod
    def get_target_in_page(self, url):
        pass

    @abstractmethod
    def get_image_url_list(self, title):
        pass

    def get_url_by_title(self, title):
        if not self._target_dic.__contains__(title):
            return None
        if not self._target_dic[title].__contains__('url'):
            return None
        return self._target_dic[title]['url']

    def get_log_path(self):
        return '{}/log.txt'.format(self.get_output_path())

    def log_all(self):
        output_path = self.get_output_path()
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        with codecs.open(self.get_log_path(), 'w', 'utf-8') as fp:
            simplejson.dump(obj=self._target_dic, fp=fp, ensure_ascii=False, indent=4)

    def read_from_log(self):
        if not os.path.exists(self.get_output_path()):
            return
        log_path = self.get_log_path()
        if not os.path.exists(log_path):
            return
        with codecs.open(log_path, 'r', 'utf-8') as fp:
            self._target_dic = simplejson.load(fp, encoding='utf-8')
            # print('_target_dic.length: {}'.format(len(self._target_dic)))
            for title in self._target_dic:
                if self._target_dic[title].__contains__('image'):
                    self._log_target_set.add(title)
            # print('_log_target_set.length: {}'.format(len(self._log_target_set)))

    @abstractmethod
    # url = params[1]
    # path = params[2]
    # target_url = params[3]
    def download_image(self, params):
        pass

    def get_folder_path(self, title):
        return '{}/{}'.format(self.get_output_path(), title)

    def get_image_path(self, title, name):
        return '{}/{}'.format(self.get_folder_path(title), name)

    def init_folder(self):
        output_path = self.get_output_path()
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        for title in self._target_dic.keys():
            path = self.get_folder_path(title)
            # print('title: {}, url: {}'.format(title, _target_dic[title]))
            if not os.path.exists(path):
                os.mkdir(path)

    @staticmethod
    def get_progress(current_number, sum_number):
        if sum_number == 0:
            return '??? ({:>4}/{:<4})'.format(current_number, sum_number)
        return '{:>7.2%} ({:>4}/{:<4})'.format(current_number / sum_number, current_number, sum_number)

    @staticmethod
    def adjust_file_name(file_name):
        return re.sub('[\\\/:\*\?"\|\<\>I]', '', file_name)

    @abstractmethod
    def calc_sum_image_number(self):
        pass
