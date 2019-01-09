from datetime import datetime
from ParserPikabu import ParserPikabu

class Main():
    def __init__(self, app_info):
        print('\033[92m' + "Загрузка модуля PIKABU" + '\033[0m')
        if not app_info:
            raise Exception("Ошибка при загрузке модуля")
        self.app_info = app_info

    def run(self):
        ENTRY_URL = self.app_info['entry_url']

        try:
            pikabu = ParserPikabu(ENTRY_URL,
                                  ['халява', 'пикабу', 'сила пикабу', 'опрос', 'в добрые руки', 'steam', 'Длиннопост',
                                   'помощь', 'арт', 'аниме', 'anime art', 'anime', 'art'], None, None, None)


            print('parsing...')
            articles = pikabu.get_articles()

            for post in articles:
                print(post)

        except Exception as err:
            print(err)
        finally:
            print('{}: ЗАВЕРШЕННО'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

if __name__ == "__main__":
    Main({'entry_url': 'https://pikabu.ru/new'}).run()