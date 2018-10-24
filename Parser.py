# -*- coding: utf-8 -*-
import codecs
import gzip
import os
import re
from abc import abstractmethod
from urllib import request, error

import simplejson
# gevent 1.2.2
from gevent import pool, monkey
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
    # 不需要抓取的 title 的位置列表
    _delete_title_pos_set = set()
    # 置顶的需要抓取的 title
    _title_list_in_top = []
    # 是否要重新获取所有的 title
    _force_refresh_all_title = False

    # 总页数
    _page_count = 0
    # 标题总数
    _title_count = 0
    # 图片总数
    _image_count = 0
    # 每一页有多少个标题
    _title_count_in_page = 0
    # 置顶标题中有多少个是需要抓取的
    _top_title_count = 0
    # 置顶标题中不需要抓取的标题的集合
    _top_no_title_set = set()

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
    # 置顶的标题个数
    def get_top_title_size(self):
        pass

    # 获取抓取的内容输出的位置
    def get_output_path(self):
        pass

    # 过滤一些标题
    def filter_title(self, title):
        return True

    @abstractmethod
    # 过滤一些图片名称
    def filter_image(self, image_name):
        return True

    @abstractmethod
    # 为了避免一些 title 是一样的, 所以需要从相应的 url 提取出一个可区分的 id
    def get_id_in_title_url(self, title, url=None):
        pass

    # 获取 title 对应的唯一标识
    def get_title_key(self, title, url=None):
        if title.find('@') != -1:
            return title
        if url is None:
            title_id = self.get_id_in_title_url(title)
        else:
            title_id = self.get_id_in_title_url(title, url=url)
        if title_id is None:
            return None
        return '{}@{}'.format(title_id, title)

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
        except BaseException as e:
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

    # 获取要抓取的网站有多少页
    # 获取要抓取的网站每页有多少标题
    # 检查置顶的 title 是否更新了
    def initiation(self):
        html = self.get_etree_html(self, self.get_home_page(), self.get_html_encoding())
        self.get_page_count(html)
        self.get_title_count_in_page(html)
        self.check_top_title_update_state(html)

    @abstractmethod
    # 获取要抓取的网站有多少页
    def get_page_count(self, html):
        pass

    @abstractmethod
    # 获取每一页中有多少个标题
    def get_title_count_in_page(self, html):
        pass

    @abstractmethod
    # 检查置顶的 title 是否更新了
    def check_top_title_update_state(self, html):
        pass

    # 获取需要抓取的页码的集合
    def get_need_page_idx_set(self):
        if self._force_refresh_all_title:
            return [page_idx for page_idx in range(1, self._page_count + 1)]
        self.update_title_idx()
        need_title_set = self.get_need_title_set()
        if self._info:
            update_title_pos_list = list(need_title_set)
            update_title_pos_list.sort()
            self._info['update_title_pos'] = update_title_pos_list
        need_page_idx_set = set()
        for title_idx in need_title_set:
            need_page_idx_set.add(self.get_page_idx_by_title_idx(title_idx))
        return need_page_idx_set

    # 获取要抓取的网站中所有的标题
    def get_all_title(self):
        self._current_page_count = 0
        self.initiation()
        self._sum_page_count = self._page_count
        print('Total page count: {}'.format(self._sum_page_count))
        self._title_count = self.get_title_count()
        need_page_idx_set = self.get_need_page_idx_set()
        self._sum_page_count = len(need_page_idx_set)
        self.write_info()
        self._pool.map(self.get_title_in_page, need_page_idx_set)

    # 获取所有标题内对应图片的地址
    def get_all_image_url(self):
        title_set = set(self._title_dic) - self._log_title_set
        self._current_title_count = 0
        self._sum_title_count = len(title_set)
        self.write_info()
        self._pool.map(self.get_image_url_list_by_title, title_set)
        self.log_all_title()

    @abstractmethod
    # 从标题对应的网页中解析图片地址的 xpath 规则
    def get_image_url_list_rule(self):
        pass

    # 获取相应页里面的所有标题
    def get_title_in_page(self, page_idx):
        url = self.get_page_url(page_idx)
        html = self.get_etree_html(self, url, self.get_html_encoding())
        self._current_page_count += 1
        print('{} page: {}'.format(self.get_progress(self._current_page_count, self._sum_page_count), url))
        a_tag_list = html.xpath(self.get_title_list_in_page_rule())
        title_count = len(a_tag_list)
        self._sum_title_count += title_count
        top_title_size = self.get_top_title_size()
        for idx in range(0, title_count):
            a_tag = a_tag_list[idx]
            title = self.get_title_in_tag(a_tag)
            title = self.adjust_file_name(title)
            if not self.filter_title(title):
                continue
            title = self.get_title_key(title, url=a_tag.attrib['href'])
            if self.get_url_by_title(title) is None:
                pos = (page_idx - 1) * self._title_count_in_page + idx + 1
                if page_idx > 1:
                    pos += top_title_size
                self._title_dic[title] = {'url': a_tag.attrib['href'], 'pos': pos}
        if title_count < self._title_count_in_page and page_idx < self._page_count:
            pos = (page_idx - 1) * self._title_count_in_page + title_count + 1
            if page_idx > 1:
                pos += top_title_size
            for idx in range(pos, pos + self._title_count_in_page - title_count):
                self._delete_title_pos_set.add(idx)
        self.log_all_title()

    @abstractmethod
    # 获得图片地址的共同前缀的最后一个字符的下标
    def get_image_url_common_prefix_idx(self, image_url):
        pass

    # 获取相应标题内所有的图片的地址
    def get_image_url_list_by_title(self, title):
        url = self.get_url_by_title(title)
        if url is None:
            return
        html = self.get_etree_html(self, url, self.get_html_encoding())
        self._current_title_count += 1
        if self._current_title_count > 0 and self._current_title_count & 0xFF == 0:
            self.log_all_title()
        print('{} title: {}'.format(self.get_progress(self._current_title_count, self._sum_title_count), title))

        img_src_list = html.xpath(self.get_image_url_list_rule())
        if len(img_src_list) == 0:
            print('Can\'t find image.({})'.format(url))
            return
        info = self._title_dic[title]
        common_prefix = img_src_list[0].strip()
        common_prefix_idx = self.get_image_url_common_prefix_idx(common_prefix)
        common_prefix = common_prefix[:common_prefix_idx]
        info['url_prefix'] = common_prefix
        info['image'] = []
        self._sum_image_count += len(img_src_list)
        for image in img_src_list:
            image_src = image.strip()
            image = image_src[common_prefix_idx:]
            if not self.filter_image(image):
                continue
            info['image'].append(image)

    # 获取相应标题的地址
    def get_url_by_title(self, title):
        if title is None:
            return None
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
            self._info = simplejson.load(fp, encoding='utf-8')
        if self._info.__contains__('delete_title_pos_list'):
            self._delete_title_pos_set = set(self._info['delete_title_pos_list'])

    # 存储要抓取的网站的相应信息到本地
    def write_info(self):
        if self._info is None:
            self._info = {}
        if self._top_title_count:
            self._info['top_title_count'] = self._top_title_count
        if self._page_count:
            self._info['page_count'] = self._page_count
        if self._title_count != 0:
            self._info['title_count'] = self._title_count
        if self._title_count_in_page:
            self._info['title_count_in_page'] = self._title_count_in_page
        if self._image_count:
            self._info['image_count'] = self._image_count
        if len(self._delete_title_pos_set) > 0:
            delete_title_pos_list = list(self._delete_title_pos_set)
            delete_title_pos_list.sort()
            self._info['delete_title_pos_list'] = delete_title_pos_list
        output_path = self.get_output_path()
        if not os.path.exists(output_path):
            os.mkdir(output_path)
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
            top_title_size = self.get_top_title_size()
            for title in self._title_dic:
                if self._title_dic[title].__contains__('image'):
                    self._log_title_set.add(title)
                if self._title_dic[title]['pos'] <= top_title_size:
                    self._title_list_in_top.append(title)
            # print('_log_target_set.length: {}'.format(len(self._log_target_set)))

    # 下载所有图片
    def download_all_image(self):
        self.init_folder()
        self._current_image_count = 0
        self.calc_sum_image_number()
        self.write_info()
        params_list = []
        for title in self._title_dic:
            info = self._title_dic[title]
            if not info.__contains__('image'):
                continue
            url_prefix = info['url_prefix']
            for image in info['image']:
                image_name = image[image.rfind('/') + 1:]
                path = self.get_image_path(title, image_name)
                if os.path.exists(path):
                    continue
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
                                         on_error=lambda e: print(
                                             'Download error: {}, in: {}\n{}'.format(url, title_url, e)))
            if content is None:
                return
            self._current_image_count += 1
            print('{} download: {}'.format(self.get_progress(self._current_image_count, self._sum_image_count), url))
            with open(path, 'wb') as fp:
                fp.write(content)

    # 获取相应标题存储的路径
    def get_title_path(self, title):
        return '{}/{}'.format(self.get_output_path(), self.get_title_key(title))

    # 获取相应图片存储的路径
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
        self._image_count = 0
        for title in self._title_dic:
            info = self._title_dic[title]
            if not info.__contains__('image'):
                continue
            for image in info['image']:
                image_name = image[image.rfind('/') + 1:]
                path = self.get_image_path(title, image_name)
                self._image_count += 1
                if not os.path.exists(path):
                    self._sum_image_count += 1

    @abstractmethod
    # 获取相应网页里面匹配标题列表的 xpath 规则
    def get_title_list_in_page_rule(self):
        pass

    @abstractmethod
    # 从含有标题的标题中获取标题
    def get_title_in_tag(self, tag):
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
        title_count = length + self._title_count_in_page * (self._sum_page_count - 1) + self._top_title_count
        print('Total title count: {}'.format(title_count))
        return title_count

    # 更新标题对应要抓取的网站中的序号
    def update_title_idx(self):
        # 如果要抓取的网站没有更新内容, 就不需要更新了
        if self._info is None \
                or self._title_count == 0 \
                or self._info['title_count'] == self._title_count:
            return
        update_count = self._title_count - self._info['title_count']
        for title in self._title_dic:
            # 如果置顶的内容改变, 那么需要重新获取所有数据, 这边代码就不会执行到了
            if self._title_dic[title]['pos'] <= self.get_top_title_size():
                continue
            self._title_dic[title]['pos'] += update_count
        # if len(self._delete_title_pos_set) > 0:
        #     pos_set = set()
        #     for pos in self._delete_title_pos_set:
        #         pos_set.add(pos + update_count)
        #     self._delete_title_pos_set = pos_set

    # 获取需要获取信息的标题列表
    def get_need_title_set(self):
        all_title_idx_set = set(range(1, self._title_count + 1))
        if self._title_count == 0:
            return all_title_idx_set
        # 获取当前已经获得标题对应链接的标题序号
        has_title_set = set()
        for title in self._title_dic:
            has_title_set.add(self._title_dic[title]['pos'])
        return all_title_idx_set - has_title_set - self._top_no_title_set - self._delete_title_pos_set

    # 获取相应标题所在的页的页码
    def get_page_idx_by_title_idx(self, title_idx):
        if self._title_count_in_page == 0:
            return 0
        top_title_size = self.get_top_title_size()
        if title_idx <= top_title_size:
            return 1
        return (title_idx + self._title_count_in_page - top_title_size - 1) // self._title_count_in_page
