# http://www.meizitu.com/
import os
import re

# gevent 1.2.2
from gevent import monkey, pool
from Parser import ParserBase


class MeizituParser(ParserBase):

    _POOL_MAX_SIZE = 256
    _pool = pool.Pool(_POOL_MAX_SIZE)

    def get_target_list(self):
        self._current_page = self._sum_page = 0
        self._current_title = self._sum_title = 0
        self._current_image = self._sum_image = 0
        count = self.get_page_number()
        self._sum_page = count
        self._pool.map(self.get_target_in_page, [idx for idx in range(1, count + 1)])
        target_set = self._target_set - self._log_target_set
        self._sum_title = len(target_set)
        self._pool.map(self.get_image_url_list, target_set)
        self.calc_sum_image_number()
        self.log_all()

    def get_home_page(self):
        return 'http://www.meizitu.com/a/more_1.html'

    def get_output_path(self):
        return './meizitu'

    def get_page_url(self, idx):
        return 'http://www.meizitu.com/a/more_{}.html'.format(idx)

    def get_page_number(self):
        html = self.get_etree_html(self, self.get_home_page(), 'gb18030')
        a_tag = html.xpath('//div[@id="wp_page_numbers"]//a')[-1]
        a_href = a_tag.attrib['href']
        return int(re.findall('\d+', a_href)[0])

    def get_target_in_page(self, page_idx):
        url = self.get_page_url(page_idx)
        html = self.get_etree_html(self, url, 'gb18030')
        self._current_page += 1
        print('{} page: {}'.format(self.get_progress(self._current_page, self._sum_page), url))
        a_tag_list = html.xpath('//*[@class="tit"]/a')
        self._sum_title += len(a_tag_list)
        for a_tag in a_tag_list:
            if a_tag.text is None:
                title = a_tag.xpath('b/text()')[0].strip()
            else:
                title = a_tag.text.strip()
            title = self.adjust_file_name(title)
            self._target_set.add(title)
            if self.get_url_by_title(title) is None:
                self._target_dic[title] = {'url': a_tag.attrib['href']}

    def get_image_url_list(self, title):
        url = self.get_url_by_title(title)
        if url is None:
            return
        html = self.get_etree_html(self, url, 'gb18030')
        self._current_title += 1
        if self._current_title > 0 and self._current_title & 0xFF == 0:
            self.log_all()
        print('{} title: {}'.format(self.get_progress(self._current_title, self._sum_title), title))

        img_src_list = html.xpath('//div[@class="postContent"]//p[1]//img/@src')
        if len(img_src_list) == 0:
            print('Can\'t find image.({})'.format(url))
            return
        info = self._target_dic[title]
        common_prefix = img_src_list[0].strip()
        common_prefix = common_prefix[:common_prefix.rfind('uploads/') + 8]
        info['url_prefix'] = common_prefix
        info['image'] = []
        self._sum_image += len(img_src_list)
        for image in img_src_list:
            image_src = image.strip()
            image = image_src[common_prefix.rfind('uploads/') + 8:]
            info['image'].append(image)

    def download_all_image(self):
        self.init_folder()
        params_list = []
        for title in self._target_dic:
            info = self._target_dic[title]
            if not info.__contains__('image'):
                continue
            url_prefix = info['url_prefix']
            for image in info['image']:
                image_name = image[image.rfind('/') + 1:]
                path = self.get_image_path(title, image_name)
                params_list.append((image_name, url_prefix + image, path, info['url']))
        self._pool.map(self.download_image, params_list)

    def download_image(self, params):
        url = params[1]
        path = params[2]
        target_url = params[3]
        if not os.path.exists(path):
            content = self.download_file(url,
                                         on_error=lambda e: print('Download error: {}, in: {}'.format(url, target_url)))
            if content is None:
                return
            self._current_image += 1
            print('{} download: {}'.format(self.get_progress(self._current_image, self._sum_image), url))
            with open(path, 'wb') as fp:
                fp.write(content)

    def calc_sum_image_number(self):
        self._sum_image = 0
        for title in self._target_dic:
            info = self._target_dic[title]
            if not info.__contains__('image'):
                continue
            for image in info['image']:
                image_name = image[image.rfind('/') + 1:]
                path = self.get_image_path(title, image_name)
                if not os.path.exists(path):
                    self._sum_image += 1


def init():
    monkey.patch_all()


def main():
    init()
    m_parser = MeizituParser()
    print(os.path.abspath(m_parser.get_output_path()))
    m_parser.read_from_log()
    m_parser.get_target_list()
    m_parser.download_all_image()


if __name__ == '__main__':
    main()
