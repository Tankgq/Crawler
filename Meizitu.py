# http://www.meizitu.com/
from Parser import ParserBase


class MeizituParser(ParserBase):

    def get_pool_max_size(self):
        return 256

    def get_html_encoding(self):
        return 'gb18030'

    def get_home_page(self):
        return 'http://www.meizitu.com/a/more_1.html'

    def get_output_path(self):
        return './meizitu'

    def get_page_url(self, idx):
        return 'http://www.meizitu.com/a/more_{}.html'.format(idx)

    def get_page_count(self):
        html = self.get_etree_html(self, self.get_home_page(), self.get_html_encoding())
        a_tag_list = html.xpath('//*[@class="tit"]/a')
        self._title_count_in_page = len(a_tag_list)
        a_href = html.xpath('//div[@id="wp_page_numbers"]//a/@href')[-1]
        return self.get_first_integer_in_string(a_href)

    def get_all_title(self):
        self._current_page_count = self._sum_page_count = 0
        self._sum_page_count = self.get_page_count()
        print('Total page count: {}'.format(self._sum_page_count))
        self._title_count = self.get_title_count()
        need_page_idx_set = self.get_need_page_idx_set()
        self._sum_page_count = len(need_page_idx_set)
        self._pool.map(self.get_title_in_page, need_page_idx_set)

    def get_title_list_in_page_rule(self):
        return '//*[@class="tit"]/a'

    def get_title_in_page(self, page_idx):
        url = self.get_page_url(page_idx)
        html = self.get_etree_html(self, url, 'gb18030')
        self._current_page_count += 1
        print('{} page: {}'.format(self.get_progress(self._current_page_count, self._sum_page_count), url))
        a_tag_list = html.xpath(self.get_title_list_in_page_rule())
        title_count = len(a_tag_list)
        self._sum_title_count += title_count
        for idx in range(0, title_count):
            a_tag = a_tag_list[idx]
            if a_tag.text is None:
                title = a_tag.xpath('b/text()')[0].strip()
            else:
                title = a_tag.text.strip()
            title = self.adjust_file_name(title)
            if self.get_url_by_title(title) is None:
                self._title_dic[title] = {'url': a_tag.attrib['href'],
                                          'pos': (page_idx - 1) * self._title_count_in_page + idx + 1}
        self.log_all_title()

    def get_all_image_url(self):
        title_set = set(self._title_dic) - self._log_title_set
        self._current_title_count = 0
        self._sum_title_count = len(title_set)
        self._pool.map(self.get_image_url_list_by_title, title_set)
        self.log_all_title()

    def get_image_url_list_by_title(self, title):
        url = self.get_url_by_title(title)
        if url is None:
            return
        html = self.get_etree_html(self, url, 'gb18030')
        self._current_title_count += 1
        if self._current_title_count > 0 and self._current_title_count & 0xFF == 0:
            self.log_all_title()
        print('{} title: {}'.format(self.get_progress(self._current_title_count, self._sum_title_count), title))

        img_src_list = html.xpath('//div[@class="postContent"]//p[1]//img/@src')
        if len(img_src_list) == 0:
            print('Can\'t find image.({})'.format(url))
            return
        info = self._title_dic[title]
        common_prefix = img_src_list[0].strip()
        common_prefix = common_prefix[:common_prefix.rfind('uploads/') + 8]
        info['url_prefix'] = common_prefix
        info['image'] = []
        self._sum_image_count += len(img_src_list)
        for image in img_src_list:
            image_src = image.strip()
            image = image_src[common_prefix.rfind('uploads/') + 8:]
            info['image'].append(image)


def main():
    m_parser = MeizituParser()
    m_parser.patch_all()
    m_parser.read_log()
    m_parser.read_info()
    m_parser.get_all_title()
    m_parser.get_all_image_url()
    m_parser.download_all_image()


if __name__ == '__main__':
    main()
