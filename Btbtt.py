# -*- coding: utf-8 -*-
import codecs
import gzip
import os
import simplejson
import time
import gevent
from gevent import monkey, pool
from lxml import etree
from urllib import request
from urllib import error

_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    'Content-Type': 'text/html;charset=UTF-8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Accept-Encoding': 'gzip, deflate'
}

_target_dic = {}
_target_image_dic = {}
_state_dic = {}
_home_page_url = 'http://www.btbtt77.com/forum-index-fid-8.htm'
_out_path = 'D:/btbtt77'
_max_thread_count = 256
_current_count = 0
_sum_count = 0
_last_print = 0
_thread_pool = pool.Pool(_max_thread_count)


def get_net_file(url, main_url):
    global _headers, _current_count
    req = request.Request(url=url, headers=_headers)
    try:
        page = request.urlopen(req)
        data = page.read()
        if page.getheader(name='Content-Encoding') == 'gzip':
            data = gzip.decompress(data)
        return data
    except BaseException as e:
        _current_count += 1
        # print('[Error] image (url: {}, main_url: {})'.format(url, main_url))

    return None


def get_html_content(url):
    global _headers
    req = request.Request(url=url, headers=_headers)
    try:
        page = request.urlopen(req)
        data = page.read()
        if page.getheader(name='Content-Encoding') == 'gzip':
            data = gzip.decompress(data)
        data = data.decode('UTF-8')
        return data
    except error.HTTPError as e:
        print('[Error] url: ' + url)

    return ''


def get_etree_html(url):
    content = get_html_content(url)
    return etree.HTML(content)


def get_page_url(idx):
    global _home_page_url
    dot_idx = _home_page_url.rfind('.')
    return '{}-page-{}{}'.format(_home_page_url[:dot_idx], idx, _home_page_url[dot_idx:])


def get_page_number():
    global _home_page_url
    html = get_etree_html(_home_page_url)
    a_page_list = html.xpath('//div[@class="page"]/a')
    for a_page in a_page_list:
        text = a_page.text
        if text.find('...') != -1:
            return int(text.replace('...', '').strip())
    return len(a_page_list) - 1


def get_target_in_page(url):
    global _target_dic
    html = get_etree_html(url)
    a_target_list = html.xpath('//td[@class="subject"]/a[2]')
    # a_target_list = filter(lambda a: a.text.lower().find('p') != -1 or a.text.find('张') != -1, a_target_list)
    for a_target in a_target_list:
        title = a_target.text.strip()
        url = a_target.attrib['href'].strip()
        if title.find('精华主题') != -1 or title.find('普通主题') != -1 or title.find('广告赞助商') != -1 or title.find('公告') != -1:
            continue
        # if title in _target_dic.keys():
        #     print('[Warning] repeat: {}, {}, {}'.format(title, _target_dic[title], url))
        _target_dic[title] = url


def init_target_list():
    global _target_dic
    number = get_page_number() + 1

    threads = []
    for idx in range(1, number):
        url = get_page_url(idx)
        threads.append(gevent.spawn(get_target_in_page, url))
    gevent.joinall(threads)


def get_folder_path(title):
    global _out_path
    return '{}/{}'.format(_out_path, title)


def get_image_path(title, name):
    return '{}/{}'.format(get_folder_path(title), name)


def init_folder():
    global _target_dic, _out_path
    if not os.path.exists(_out_path):
        os.mkdir(_out_path)
    for title in _target_dic.keys():
        path = get_folder_path(title)
        # print('title: {}, url: {}'.format(title, _target_dic[title]))
        if not os.path.exists(path):
            os.mkdir(path)


def get_image_url_list(title):
    global _target_image_dic, _target_dic, _current_count, _sum_count, _last_print
    url = _target_dic[title]
    _target_image_dic[title] = {}
    target_image_list = _target_image_dic[title]
    html = get_etree_html(url)
    if html is None:
        return
    image_list = html.xpath('//div[@class="message"]//img')
    if len(image_list) == 0:
        return
    common_prefix = image_list[0].attrib['src'].strip()
    common_prefix = common_prefix[:common_prefix.rfind('000/') + 4]
    target_image_list['url_prefix'] = common_prefix
    target_image_list['url'] = url
    target_image_list['image'] = []
    for image in image_list:
        image_src = image.attrib['src'].strip()
        if image_src.find('.gif') != -1:
            # print('[Warning] image_src: {}, url: {}'.format(image_src, url))
            continue
        image = image_src[image_src.rfind('000/') + 4:]
        target_image_list['image'].append(image)
    _current_count += 1
    # if (_current_count - _last_print) / _max_thread_count > 0.01 or _current_count == _sum_count:
    #     _last_print = _current_count
    # print('[Get] {:>7.2%} ({:>4}/{:<4})'.format(_current_count / _sum_count, _current_count, _sum_count))


def init_target_image_list():
    global _target_dic, _sum_count, _current_count, _last_print, _thread_pool
    _sum_count = len(_target_dic)
    _current_count = 0
    _last_print = _current_count
    _thread_pool.map(get_image_url_list, _target_dic.keys())


def log_target_image_list():
    global _out_path, _current_count, _sum_count, _last_print
    if not os.path.exists(_out_path):
        os.mkdir(_out_path)
    _current_count = 0
    _sum_count = 0
    _last_print = _current_count
    with codecs.open('{}/log.txt'.format(_out_path), 'w', 'utf-8') as fp:
        simplejson.dump(obj=_target_image_dic, fp=fp, ensure_ascii=False, indent=4)
        # for title in _target_image_dic:
        #     image_src_list = _target_image_dic[title]
        #     _sum_count += len(image_src_list)
        #     fp.write('title: {}, url: {}'.format(title, _target_dic[title]) + os.linesep)
        #     for image_src in image_src_list:
        #         fp.write('\tsrc: {}'.format(image_src) + os.linesep)


def download_file(params):
    global _current_count, _sum_count, _max_thread_count, _last_print
    url = params[1]
    path = params[2]
    main_url = params[3]
    if not os.path.exists(path):
        content = get_net_file(url, main_url)
        if content is None:
            return
        with open(path, 'wb') as fp:
            fp.write(content)
    _current_count = _current_count + 1
    # if (_current_count - _last_print) / _sum_count > 0.01 or _current_count == _sum_count:
    #     _last_print = _current_count
    # print('[Download] {:>7.2%} ({}/{}), url: {}'.format(_current_count / _sum_count, _current_count, _sum_count, url))


def get_all_image_file():
    global _target_image_dic, _target_dic, _current_count, _last_print, _thread_pool, _sum_count
    _current_count = 0
    _last_print = _current_count
    params_list = []
    for title in _target_image_dic:
        info = _target_image_dic[title]
        url_prefix = info['url_prefix']
        for image in info['image']:
            image_name = image[image.rfind('/') + 1:]
            path = get_image_path(title, image_name)
            params_list.append((image_name, url_prefix + image, path, _target_dic[title]))
    _sum_count = len(params_list)
    _thread_pool.map(download_file, params_list)


if __name__ == '__main__':
    monkey.patch_all()
    op = time.time()
    init_target_list()
    ed = time.time()
    print('Get target list total time: {:.3f} ms'.format((ed - op) * 1000))
    print('Count: {}'.format(len(_target_dic)))
    op = time.time()
    init_target_image_list()
    ed = time.time()
    print('Get image src total time: {:.3f} ms'.format((ed - op) * 1000))
    log_target_image_list()
    init_folder()
    op = time.time()
    get_all_image_file()
    ed = time.time()
    print('Download image total time: {:.3f} ms'.format((ed - op) * 1000))
