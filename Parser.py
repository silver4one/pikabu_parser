import re
import requests
import time
from requests.exceptions import RequestException
from datetime import datetime
from lxml import html

headers = requests.utils.default_headers()
headers.update(
	{
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36 OPR/56.0.3051.52 (Edition Yx)',
	}
)

class IParser(object):

	def __init__(self, url, miss_tags, public_tags=True):
		self.entry_url = url
		self.base_url = re.search(r'((http[s]?)://[^/]+)', url).group(1)
		self._pre = re.search(r'((http[s]?)://[^/]+)', url).group(2)
		self.entry_tree = None
		self.miss_tags = miss_tags or []
		self.public_tags = public_tags
		self.article_html = ''

	def get_articles(self):
		list_articles = self.get_list_articles()
		list_articles.reverse()
		self._exclude_posts(list_articles)
		articles = self._get_formated_articles(list_articles)
		return articles

	def _get_formated_articles(self, list_articles):
		formated_articles = []
		for article in list_articles:
			error_text = []
			article_link = article['Link']
			formated_text = []
			article_imgs = []
			article_videos = []
			article_tags = []
			public = True

			self._db_log('Парсинг: {0}'.format(article_link))

			article_tree = self._get_article(article_link)
			if article_tree == None:
				self._db_log('Ошибка в ид: {}'.format(article_link))
				return formated_articles

			self.timer(0)

			article_date = self._get_article_date(article_tree)

			article_title = self._get_article_title(article_tree)
			if not article_title:
				self._db_log('Ошибка в заголовке: {}'.format(article_link))
				continue

			formated_text.append(article_title)
			formated_text.append('\r\n\r\n')

			article_img = self._get_article_images(article_tree)
			article_videos = self._get_article_videos(article_tree)
			formated_text += self._get_formated_text(article_tree)

			article_tags = self._get_article_tags(article_tree)
			public = self._miss_to_tags(article_tags)
			if not public:
				error_text.append('Присутствует тэг из списка"{0}"'.format(','.join(self.miss_tags)))

			if self.public_tags and article_tags:
				formated_text.append('\r\n\r\n')
				formated_text.append(' '.join(article_tags))

			if len(''.join(formated_text).replace(" ", "")) >= 7000:
				public = False
				self._db_log('Текст длинный, пост ид: {}'.format(article['Id']))
				error_text.append('Текст длинный, пост ид: {}'.format(article['Id']))

			if self._igonre_article(article_tree):
				self._db_log('Игнорирование, пост ид: {}'.format(article['Id']))
				formated_articles.append({'Id': article['Id'], 'Link': article_link, 'Text': ''.join(formated_text), 'Picture': article_img,
					'Video': article_videos, 'Published': article_date, 'Public': False, 'Error': 'Игнорирован'})
				continue

			formated_articles.append({'Id': article['Id'], 'Link': article_link, 'Text': ''.join(formated_text), 'Picture': article_img,
				'Video': article_videos, 'Published': article_date, 'Public': public, 'Error': '|'.join(error_text)})

		return formated_articles

	def get_list_articles(self):
		list_articles_id = []
		if self._get_tree():
			if self._is_blocks():
				for block in self._get_blocks():
					try:
						if self._not_missing_article(block):
							article_id = self._get_article_id(block)
							if not article_id: continue
							list_articles_id.append({'Id': article_id, 'Link': self._normalize_url(self._get_article_link(block))})
					except IndexError:
						continue
		return list_articles_id

	def _normalize_url(self, url):
		_pre = self._pre
		if not re.search(self.base_url, url) and not re.search(r'http[s]?', url):
			if url[:1] == '/' and url[:2] != '//':
				return self.base_url + url
			elif url[:2] == '//':
				return _pre + url
			else:
				return self.base_url + '/' + url
		return url

	def _exclude_posts(self, list_articles_id):
		to_rem = []
		for article_id in list_articles_id:
			if self._db_exist_article(article_id['Id']):
				to_rem.append(article_id)
				self._db_log('Уже есть: {}'.format(article_id['Id']))
		for r in to_rem:
			list_articles_id.remove(r)

	def _db_exist_article(self, article_id):
		'''Проверяет есть ли статья в БД'''
		return False

	def _db_log(self, log_text):
		'''Лог'''
		print(log_text)

	def _is_blocks(self):
		'''Проверяет является ли объект подходящим блоком'''
		return False

	def _igonre_article(self, article_tree):
		'''Игнорировать статью'''
		return False

	def _get_blocks(self):
		'''Возвращает массив блоков lxml'''
		raise NotImplementedError

	def _get_article_link(self, block_tree):
		'''Возвращает ссылку на статью'''
		raise NotImplementedError

	def _get_article(self, article_link):
		'''Возвращает объект статьи'''
		try:
			data = requests.get(article_link, headers=headers)
			self.article_html = data.content
		except RequestException as err:
			self._db_log('Ошибка: {0}'.format(err))
			return None

		return html.document_fromstring(data.content)

	def _get_article_title(self, article_tree):
		'''Возвращает заголовок статьи'''
		raise NotImplementedError

	def _get_formated_text(self, article_tree):
		'''Возврощает текст статьи'''
		raise NotImplementedError

	def _get_article_images(self, article_tree):
		'''Возврощает массив найденых изображений'''
		return [{'src': None, 'img_alt': None}]

	def _get_article_videos(self, article_tree):
		'''Возврощает массив найденных видео ссылок'''
		raise NotImplementedError

	def _get_article_date(self, article_tree):
		'''Возврощает дату статьи'''
		return datetime.now()

	def _get_article_id(self, block_tree):
		'''Возврощает ид статьи'''
		raise NotImplementedError

	def _get_article_tags(self, article_tree):
		'''Возврощает массив тэгов'''
		return []

	def _miss_to_tags(self, article_tags):
		'''Не публиковать статью тэги совпадают'''
		if self.miss_tags:
			for atags in article_tags:
				for mtags in self.miss_tags:
					if atags.find(mtags.lower()) > -1:
						self._db_log('Не публикуем, присутсвует тэг "{}"'.format(mtags))
						return False
		return True

	def _missing_article(self):
		'''Условия при которых статья считается не публикуемой'''
		return False

	def _not_missing_article(self, block_tree):
		'''Условия при которых статья считается публикуемой <не обезательный метод>'''
		return True

	def _get_tree(self):
		try:
			data = requests.get(self.entry_url, headers=headers)
		except RequestException as err:
			self._db_log('Ошибка: {0}'.format(err))
			return False
		else:
			self.entry_tree = html.fromstring(data.content)
		return True

	def remove_class_tree(self, article_tree, remclass):
		for tree in article_tree:
			rm = tree.xpath('.//*[contains(@class, "' + remclass + '")]')
			for r in rm:
				r.getparent().remove(r)

	def clear_text(self, text):
		return re.sub("(\r\n|\n)", ' ', text)

	def timer(self, seconds):
		time.sleep(seconds)