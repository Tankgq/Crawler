# -*- coding: utf-8 -*-
# http://www.mmjpg.com/
from Parser import ParserBase


class MmjpgParser(ParserBase):
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
        'Content-Type': 'text/html;charset=UTF-8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Referer': 'http://www.mmjpg.com/mm/1508', # asd
        'Cache-Control': 'max-age=0',
        'Accept-Encoding': 'gzip, deflate'
    }

    def get_pool_max_size(self):
        return 256

    def get_html_encoding(self):
        return 'utf-8'

    def get_home_page(self):
        return 'http://www.mmjpg.com/'

    def get_top_title_size(self):
        return 0

    def get_output_path(self):
        return './mmjpg'

    def get_id_in_title_url(self, title, url=None):
        if url is None:
            url = self.get_url_by_title(title)
            if url is None:
                return None
        return url[url.rfind('/') + 1:]

    def get_page_url(self, idx):
        if idx == 1:
            return self.get_home_page()
        return 'http://www.mmjpg.com/home/{}'.format(idx)

    def get_page_count(self, html):
        a_text = html.xpath('//div[@class="page"]/a/text()')[-2]
        self._page_count = self.get_first_integer_in_string(a_text)

    def get_title_count_in_page(self, html):
        a_tag_list = html.xpath(self.get_title_list_in_page_rule())
        self._top_title_count = 0
        top_title_size = self.get_top_title_size()
        for idx in range(0, top_title_size):
            text = a_tag_list[idx].text.strip()
            if self.filter_title(text):
                self._top_title_count += 1
            else:
                self._top_no_title_set.add(idx + 1)
        self._title_count_in_page = len(a_tag_list) - top_title_size

    def check_top_title_update_state(self, html):
        a_tag_list = html.xpath(self.get_title_list_in_page_rule())
        top_title_size = self.get_top_title_size()
        for idx in range(0, top_title_size):
            a_tag = a_tag_list[idx]
            title = self.get_title_in_tag(a_tag)
            title = self.adjust_file_name(title)
            if not self.filter_title(title):
                continue
            title = self.get_title_key(title, url=a_tag.attrib['href'])
            if title not in self._title_list_in_top:
                self._force_refresh_all_title = True
                return
        self._force_refresh_all_title = False

    def get_title_list_in_page_rule(self):
        return '//a[contains(@class,"subject_link")]'

    def filter_title(self, title):
        return True

    def filter_image(self, image_name):
        return True

    def get_title_in_tag(self, tag):
        return tag.text.strip()

    def get_image_url_list_rule(self):
        return '//div[@class="message"]//img/@src'

    def get_image_url_common_prefix_idx(self, image_url):
        return image_url.rfind('/') + 1


def main():
    m_parser = MmjpgParser()
    # m_parser.patch_all()
    # m_parser.read_log()
    # m_parser.read_info()
    # m_parser.get_all_title()
    # m_parser.get_all_image_url()
    # m_parser.download_all_image()
    print(m_parser.get_html_content('http://www.mmjpg.com/data.php?id=1508&page=8999'))


if __name__ == '__main__':
    main()