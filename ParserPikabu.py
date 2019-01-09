import re
import time
from datetime import datetime

import Parser

class ParserPikabu(Parser.IParser):

    _ignore = ['pikabu', 'пикабу', '#comment_', 'пикабу', 'пиka', 'пика', 'пикабуу', 'пикабушники', 'пикабушник']

    def __init__(self, url, miss_tags, appinfo, appid, db, only_with_media=True):
        super().__init__(url, miss_tags, False)
        self.APPID = appid
        self.DB = db
        self.appinfo = appinfo
        self.only_with_media = only_with_media

    def _db_exist_article(self, article_id):
        return False

    def _is_blocks(self):
        return len(self.entry_tree.xpath('//*[@class="main"]//*[@class="stories-feed"]')) > 0

    def _igonre_article(self, article_tree):
        if not self.only_with_media:
            self.only_with_media = True
            return True

        content = article_tree.xpath('.//*[contains(@class, "story__content")]//p//text()')

        text = ''.join(content).strip()
        try:
            text = text.encode('iso-8859-1').decode('1251', 'ignore')
        except Exception as err:
            print(err)
            pass

        for ign in self._ignore:
            if text.lower().find(ign) > -1:
                return True

        return False

    def _get_blocks(self):
        return self.entry_tree.xpath('//article[@class="story"][@data-story-id]')

    def _get_article_link(self, block_tree):
        return block_tree.xpath('.//*[@class="story__title"]/a/@href')[0]

    def _get_article_id(self, block_tree):
        return block_tree.xpath('./@data-story-id')[0]

    def _get_article_title(self, article_tree):
        for title in article_tree.xpath('.//*[@class="story__title"]//*[contains(@class, "story__title-link")]/text()'):
            return title.encode('iso-8859-1').decode('1251', 'ignore').replace('\xa0', ' ')

    def _get_article_date(self, article_tree):
        article_date = re.search(r'<time.+datetime=[\"]?([^\"]+)', str(self.article_html)).group(1)
        return self.to_datime(article_date)

    def _get_article_tags(self, article_tree):
        tags = []
        for tag_a in article_tree.xpath('.//*[@class="story__tags tags"]/a/text()'):
            tag_a = tag_a.encode('raw-unicode-escape').decode('utf-8', 'ignore')
            tags.append('#' + tag_a.lower().replace(" ","").replace(".","_").replace("(","_").replace(")","_").replace("&ndsp","_"))
        return tags

    def _get_formated_text(self, article_tree):
        article_text = []

        content_tree = article_tree.xpath('.//*[contains(@class, "story__content")]//p')
        if not content_tree:
            content_tree = article_tree.xpath('.//*[contains(@class, "story__content_type_text")]')

        for content in content_tree:
            text = "".join(content.xpath('.//text()')).strip()

            try:
                text = text.encode('iso-8859-1').decode('1251', 'ignore')
                text = text.replace('\xa0', ' ')
            except Exception:
                text = ''
                self.only_with_media = False

            article_text.append(text)

            article_text.append('\r\n')

        return article_text

    def _get_article_images(self, article_tree):
        article_imgs = []

        images = article_tree.xpath('.//article[@class="story"]//*[contains(@class, "story__content")]//a[@data-lightbox]')
        for img in images:
            img_alt = ''
            if 'title' in img.attrib:
                img_alt = img.attrib['title']
            elif 'alt' in img.attrib:
                img_alt = img.attrib['alt']

            img_src = img.attrib['href']
            try:
                img_alt = img_alt.encode('iso-8859-1').decode('1251', 'ignore')
                img_alt = ''.join(img_alt.split(',')[:1]).replace('\xa0', ' ')
            except:
                img_alt = ''

            article_imgs.append({'src': self._normalize_url(img_src), 'title': img_alt})

        images = article_tree.xpath('.//*[contains(@class, "story__content")]//*[contains(@class, "story-block_type_image")]//img[not(@class)]')
        images += article_tree.xpath('.//*[contains(@class, "story-block_type_image")]//*[@class="player"]')

        for img in images:
            img_alt = ''
            if 'class' in img.attrib and img.attrib['class'] == 'player':
                continue

            if 'title' in img.attrib:
                img_alt = img.attrib['title']
            elif 'alt' in img.attrib:
                img_alt = img.attrib['alt']

            try:
                img_src = img.attrib['data-large-image']
                if len(img_src) < 2:
                    img_src = img_src.attrib['src']
            except KeyError:
                try:
                    img_src = img.attrib['src']
                except KeyError:
                    img_src = img.attrib['data-source']

            try:
                img_alt = img_alt.encode('iso-8859-1').decode('1251', 'ignore')
                img_alt = ''.join(img_alt.split(',')[:1]).replace('\xa0', ' ')
            except Exception:
                img_alt = ''

            article_imgs.append({'src': self._normalize_url(img_src), 'title': img_alt})

        if not self.only_with_media:
            self.only_with_media = len(article_imgs) > 0

        return article_imgs

    def _get_article_videos(self, article_tree):
        article_videos = []
        videos = article_tree.xpath('//*[@class="player"][@data-type="video"]')
        title = ''
        for video in videos:
            video_src = video.attrib['data-source']
            if video_src.find("www.youtube.com") and video_src[0:2:1] == '//':
                video_src = "https:" + video_src
            #if re.search(r"youtube", video_src):
            #	id = re.search(r"/([A-z0-9-]{10,15})(\?)?", video_src).group(1)

            article_videos.append({'src': video_src, 'title': title})

        if not self.only_with_media:
            self.only_with_media = len(article_videos) > 0

        return article_videos

    def to_datime(self, str_datime):
        str_datime = re.search(r'(\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2}:\d{2})', str_datime).group(1)
        str_datime = str_datime.lower()

        try:
            return datetime.strptime(str_datime, '%Y-%m-%dt%H:%M:%S')
        except:
            try:
                return datetime.strptime(str_datime, '%Y-%m-%d %H:%M:%S')
            except:
                return datetime.strptime('2017-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')

    def timer(self, seconds):
        if not self.appinfo:
            time.sleep(seconds)
            return
        tic = 0
        while True:
            if tic >= seconds:
                break
            time.sleep(1)
            tic += 1