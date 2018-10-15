# -*- coding: utf-8 -*-
from Parser import ParserBase


class BtbttParser(ParserBase):

    def get_pool_max_size(self):
        return 256

    def get_html_encoding(self):
        return 'utf-8'

    def get_home_page(self):
        return 'http://www.btjia.com/forum-index-fid-8-page-1.htm'

    def get_top_title_size(self):
        return 3

    def get_output_path(self):
        return './btbtt'

    def get_page_url(self, idx):
        return 'http://www.btjia.com/forum-index-fid-8-page-{}.htm'.format(idx)

    def get_page_count(self):
        html = self.get_etree_html(self, self.get_home_page(), self.get_html_encoding())
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
        a_text = html.xpath('//div[@class="page"]/a/text()')[-2]
        return self.get_first_integer_in_string(a_text)

    def get_title_list_in_page_rule(self):
        return '//a[contains(@class,"subject_link")]'

    def filter_title(self, title):
        return not (title.find('精华主题') != -1 or
                    title.find('普通主题') != -1 or
                    title.find('广告赞助商') != -1 or
                    title.find('公告') != -1)

    def filter_image(self, image_name):
        return not image_name.find('.gif') != -1

    def get_title_in_tag(self, tag):
        return tag.text.strip()

    def get_image_url_list_rule(self):
        return '//div[@class="message"]//img/@src'

    def get_image_url_common_prefix_idx(self, image_url):
        return image_url.rfind('000/') + 4


def main():
    m_parser = BtbttParser()
    m_parser.patch_all()
    m_parser.read_log()
    m_parser.read_info()
    m_parser.get_all_title()
    m_parser.get_all_image_url()
    m_parser.download_all_image()


if __name__ == '__main__':
    main()
