# -*- coding: utf-8 -*-
import simplejson
import codecs
import gzip
import re
import os

from urllib import request, error
# gevent 1.2.2
from gevent import pool, monkey
from abc import abstractmethod
from lxml import etree


class ParserBase(object):

    _headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
        'Content-Type': 'text/html;charset=UTF-8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Accept-Encoding': 'gzip, deflate'
    }

    # 线程池
    _pool = None
    # 键为标题, 存储标题对应的图片列表
    _title_dic = {}
    # 已经存储在本地日志内且已获得标题对应链接的标题集合
    _log_title_set = set()
    # 网站的状态, 如最新的标题, 以及当前获得的标题的总数等
    _info = None

    # 标题总数
    _title_count = 0
    # 每一页有多少个标题
    _title_count_in_page = 0

    # 需要获取的页数
    _current_page_count = _sum_page_count = 0
    # 需要获取的标题数量
    _current_title_count = _sum_title_count = 0
    # 需要获取的图片数量
    _current_image_count = _sum_image_count = 0

    def __init__(self):
        self._pool = pool.Pool(self.get_pool_max_size())
        print('Output path: {}'.format(os.path.abspath(self.get_output_path())))

    @staticmethod
    # 打下猴子补丁
    def patch_all():
        monkey.patch_all()

    @abstractmethod
    # 获取线程池的最大容量
    def get_pool_max_size(self):
        pass

    @abstractmethod
    # 获取当前要抓取的网页的编码
    def get_html_encoding(self):
        pass

    @abstractmethod
    # 获取当前要抓取的网站的首页
    def get_home_page(self):
        pass

    @abstractmethod
    # 获取抓取的内容输出的位置
    def get_output_path(self):
        pass

    # 获得网页的内容
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

    # 下载文件
    def download_file(self, url, on_error=None):
        return self.get_html_content(url, on_error=on_error, encoding=None)

    @staticmethod
    # 使用 etree 解析相应网站的内容
    def get_etree_html(self, url, encoding='utf-8'):
        content = self.get_html_content(url, encoding=encoding)
        return etree.HTML(content)

    @abstractmethod
    # 获取对应页数的网址
    def get_page_url(self, idx):
        pass

    @abstractmethod
    # 获取要抓取的网站有多少页
    # 获取要抓取的网站每页有多少标题
    def get_page_count(self):
        pass

    # 获取需要抓取的页码的集合
    def get_need_page_idx_set(self):
        self.update_title_idx()
        need_title_set = self.get_need_title_set()
        need_page_idx_set = set()
        for title_idx in need_title_set:
            need_page_idx_set.add(self.get_page_idx_by_title_idx(title_idx))
        return need_page_idx_set

    @abstractmethod
    # 获取要抓取的网站中所有的标题
    def get_all_title(self):
        pass

    @abstractmethod
    # 获取所有标题内对应图片的地址
    def get_all_image_url(self):
        pass

    @abstractmethod
    # 获取相应页里面的所有标题
    def get_title_in_page(self, url):
        pass

    @abstractmethod
    # 获取相应标题内所有的图片的地址
    def get_image_url_list_by_title(self, title):
        pass

    # 获取相应标题的地址
    def get_url_by_title(self, title):
        if not self._title_dic.__contains__(title):
            return None
        if not self._title_dic[title].__contains__('url'):
            return None
        return self._title_dic[title]['url']

    # 获取日志的路径
    def get_log_path(self):
        return '{}/log.json'.format(self.get_output_path())

    # 获取存储抓取网站信息的路径
    def get_info_path(self):
        return '{}/info.json'.format(self.get_output_path())

    # 读取存储在本地的网站信息
    def read_info(self):
        info_path = self.get_info_path()
        if not os.path.exists(info_path):
            return
        with codecs.open(info_path, 'r', 'utf-8') as fp:
            _info = simplejson.load(fp, encoding='utf-8')

    # 存储要抓取的网站的相应信息到本地
    def write_info(self):
        if self._info is None:
            self._info = {}
        self._info['title_count'] = self._sum_title_count
        self._info['title_count_in_page'] = self._title_count_in_page
        self._info['page_count'] = self._sum_page_count
        with codecs.open(self.get_info_path(), 'w', 'utf-8') as fp:
            simplejson.dump(obj=self._info, fp=fp, ensure_ascii=False, indent=4)

    # 记录所有的标题及标题对应的信息到本地
    def log_all_title(self):
        output_path = self.get_output_path()
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        with codecs.open(self.get_log_path(), 'w', 'utf-8') as fp:
            simplejson.dump(obj=self._title_dic, fp=fp, ensure_ascii=False, indent=4)

    # 从日志中读取所有标题以及存储的相应信息
    def read_log(self):
        if not os.path.exists(self.get_output_path()):
            return
        log_path = self.get_log_path()
        if not os.path.exists(log_path):
            return
        with codecs.open(log_path, 'r', 'utf-8') as fp:
            self._title_dic = simplejson.load(fp, encoding='utf-8')
            # print('_target_dic.length: {}'.format(len(self._target_dic)))
            for title in self._title_dic:
                if self._title_dic[title].__contains__('image'):
                    self._log_title_set.add(title)
            # print('_log_target_set.length: {}'.format(len(self._log_target_set)))

    # 下载所有图片
    def download_all_image(self):
        self.init_folder()
        self._current_image_count = 0
        self.calc_sum_image_number()
        params_list = []
        for title in self._title_dic:
            info = self._title_dic[title]
            if not info.__contains__('image'):
                continue
            url_prefix = info['url_prefix']
            for image in info['image']:
                image_name = image[image.rfind('/') + 1:]
                path = self.get_image_path(title, image_name)
                params_list.append((image_name, url_prefix + image, path, info['url']))
        self._pool.map(self.download_image, params_list)

    # 下载相应图片
    # @param params[0] image_name, 图片名称
    # @param params[1] url, 图片地址
    # @param params[2] path, 图片存储路径
    # @param params[3] title_url, 图片所在标题的地址
    def download_image(self, params):
        url = params[1]
        path = params[2]
        title_url = params[3]
        # 如果图片已经存在就需要下载了
        if not os.path.exists(path):
            content = self.download_file(url,
                                         on_error=lambda e: print('Download error: {}, in: {}'.format(url, title_url)))
            if content is None:
                return
            self._current_image_count += 1
            print('{} download: {}'.format(self.get_progress(self._current_image_count, self._sum_image_count), url))
            with open(path, 'wb') as fp:
                fp.write(content)

    # 获取相应标题存储的路径
    def get_title_path(self, title):
        return '{}/{}'.format(self.get_output_path(), title)

    # 获取想应图片存储的路径
    def get_image_path(self, title, name):
        return '{}/{}'.format(self.get_title_path(title), name)

    # 初始化文件夹
    def init_folder(self):
        output_path = self.get_output_path()
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        for title in self._title_dic.keys():
            path = self.get_title_path(title)
            # print('title: {}, url: {}'.format(title, _title_dic[title]))
            if not os.path.exists(path):
                os.mkdir(path)

    @staticmethod
    # 获取相应的进度信息
    def get_progress(current_number, sum_number):
        if sum_number == 0:
            return '??? ({:>4}/{:<4})'.format(current_number, sum_number)
        return '{:>7.2%} ({:>4}/{:<4})'.format(current_number / sum_number, current_number, sum_number)

    @staticmethod
    # 调整文件名让其符合 Window 文件或文件夹的命名规则
    def adjust_file_name(file_name):
        return re.sub('[\\\/:\*\?"\|\<\>I]', '', file_name)

    @staticmethod
    # 获取相应字符串中第一串数字
    def get_first_integer_in_string(target_string):
        return int(re.findall('\d+', target_string)[0])

    # 获取需要下载的图片总数, 不包括已经下载好的
    def calc_sum_image_number(self):
        self._sum_image_count = 0
        for title in self._title_dic:
            info = self._title_dic[title]
            if not info.__contains__('image'):
                continue
            for image in info['image']:
                image_name = image[image.rfind('/') + 1:]
                path = self.get_image_path(title, image_name)
                if not os.path.exists(path):
                    self._sum_image_count += 1

    @abstractmethod
    # 获取相应页里面匹配标题列表的 xpath 规则
    def get_title_list_in_page_rule(self):
        pass

    # 获取要抓取的网站中的标题总数, 主要是为了确认要抓取的网站中新增了多少个标题
    def get_title_count(self):
        if self._sum_page_count == 0 or self._title_count_in_page == 0:
            return 0
        url = self.get_page_url(self._sum_page_count)
        html = self.get_etree_html(self, url, self.get_html_encoding())
        a_tag_list = html.xpath(self.get_title_list_in_page_rule())
        length = len(a_tag_list)
        if length == 0:
            return 0
        title_count = length + self._title_count_in_page * (self._sum_page_count - 1)
        print('Total title count: {}'.format(title_count))
        return title_count

    # 更新标题对应要抓取的网站中的序号
    def update_title_idx(self):
        # 如果要抓取的网站没有更新内容, 就不需要更新了
        if self._info is None \
                or self._sum_title_count == 0 \
                or self._info['title_count'] == self._sum_title_count:
            return
        update_count = self._sum_title_count - self._info['title_count']
        for title in self._title_dic:
            self._title_dic[title]['pos'] += update_count

    # 获取需要获取信息的标题列表
    def get_need_title_set(self):
        all_title_idx_set = set(range(1, self._title_count + 1))
        if self._title_count == 0:
            return all_title_idx_set
        # 获取当前已经获得标题对应链接的标题序号
        has_title_set = set()
        for title in self._title_dic:
            pos = self._title_dic[title]['pos']
            has_title_set.add(self._title_dic[title]['pos'])
        return all_title_idx_set - has_title_set

    # 获取相应标题所在的页的页码
    def get_page_idx_by_title_idx(self, title_idx):
        if self._title_count_in_page == 0:
            return 0
        return (title_idx + self._title_count_in_page - 1) // self._title_count_in_page
