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
        a_tag_list = html.xpath(self.get_title_list_in_page_rule())
        self._title_count_in_page = len(a_tag_list)
        a_href = html.xpath('//div[@id="wp_page_numbers"]//a/@href')[-1]
        return self.get_first_integer_in_string(a_href)

    def get_title_list_in_page_rule(self):
        return '//*[@class="tit"]/a'

    def get_title_in_tag(self, tag):
        if tag.text is None:
            title = tag.xpath('b/text()')[0].strip()
        else:
            title = tag.text.strip()
        return title

    def get_image_url_list_rule(self):
        return '//div[@class="postContent"]//p[1]//img/@src'

    def get_image_url_common_prefix_idx(self, image_url):
        return image_url.rfind('uploads/') + 8


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
