import re

import aiofiles
import aiohttp
import asyncio
import json
import os

from bs4 import BeautifulSoup


def fix_image_url(url):
    # Заменяем часть URL
    url = url.replace('panduit-h.assetsadobe.com/is/image/content/dam/panduit/en/products/assets/',
                      'www.panduit.com/content/dam/panduit/en/products/assets/')

    # Удаляем часть URL
    url = url.split('?')[0]

    return url


def clean_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)


async def download_image(session, url, filename):
    async with session.get(url) as response:
        response.raise_for_status()

        # Получаем расширение файла изображения
        ext = url.split('.')[-1]

        # Создаем директорию для сохранения изображений, если ее нет
        if not os.path.exists('images'):
            os.makedirs('images')

        # Сохраняем изображение
        async with aiofiles.open(f'images/{clean_filename(filename)}.{ext}', 'wb') as file:
            await file.write(await response.read())


async def save_images(image_urls, sku):
    # Создаем директорию для сохранения изображений, если ее нет
    if not os.path.exists('images'):
        os.makedirs('images')

    # Инициализируем сессию aiohttp
    async with aiohttp.ClientSession() as session:
        # Создаем список для записи данных
        tasks = []

        # Сохраняем каждое изображение
        for idx, image_url in enumerate(image_urls, start=1):
            tasks.append(download_image(session, image_url, f'{sku}_{idx}'))

        # Запускаем все задачи асинхронно
        await asyncio.gather(*tasks)


async def handle_page(session, url):
    # Получим содержимое страницы в переменную resp
    async with session.get(url) as resp:
        resp.raise_for_status()

        # Создадим пустой список для URL изображений
        image_urls = []

        # Создадим пустой список для данных из элементов breadcrumb-item
        breadcrumb_items = []

        # Создадим список для хранения ключей и значений из таблицы
        table_data = {}

        # Парсим страницу с помощью BeautifulSoup
        soup = BeautifulSoup(await resp.text(), 'html.parser')

        # Найдем элементы с классом 'title h1' и 'h3' и получим их текст
        title = soup.find('h1', class_='title h1').text.strip()
        sku = soup.find('h3', class_='h3').text.strip()
        # Получим текст из элемента с классом 'description'
        description = soup.find('p', class_='description').text.strip()

        # Найдем тег 'ul' с классом 'list-unstyled thumbs'
        ul_tag = soup.find('ul', class_='list-unstyled thumbs')

        # Если тег найден
        if ul_tag:
            # Найдем все теги 'img' внутри тега 'ul'
            for img_tag in ul_tag.find_all('img'):
                # Добавим значение атрибута 'src' каждого тега 'img' в список image_urls
                image_urls.append(fix_image_url(img_tag['src']))

        # Проверяем наличие нужного элемента
        collapse_one_div = soup.find('div', id='collapseOne')
        if collapse_one_div:
            # Ищем все элементы 'tr' внутри div с id 'collapseOne'
            for tr in collapse_one_div.find_all('tr'):
                # Получаем все элементы <td> внутри текущего элемента <tr>
                tds = tr.find_all('td')

                # Если в <tr> есть два <td>, добавляем ключ и значение в словарь
                if len(tds) == 2:
                    key = tds[0].text.strip()
                    value = tds[1].text.strip()

                    table_data[key] = value

        # Найдем все элементы с классом 'breadcrumb-item'
        breadcrumb_items_tags = soup.find_all('li', class_='breadcrumb-item')

        # Переберем все элементы и добавим текст ссылок в список breadcrumb_items
        for breadcrumb_item_tag in breadcrumb_items_tags:
            breadcrumb_item_text = breadcrumb_item_tag.get_text(strip=True)
            breadcrumb_items.append(breadcrumb_item_text)

        # Выведем данные
        print("Title:", title)
        print("SKU:", sku)
        print("Description:", description)
        print("Image URLs:", image_urls)
        print("Breadcrumb Items:", breadcrumb_items)
        print("Table Data:", table_data)
        print()

        # Объединяем элементы breadcrumb_items в одну строку через " > "
        breadcrumb_path = " > ".join(breadcrumb_items[2:])

        # Возвращаем данные
        return {
            'title': title,
            'sku': sku,
            'description': description,
            'image_urls': image_urls,
            'breadcrumb_path': breadcrumb_path,
            'table_data': table_data
        }


async def main():
    # Загрузим список ссылок из файла 'test.txt'
    with open('new_links.txt', 'r') as file:
        links = file.readlines()

    # Инициализируем сессию aiohttp
    async with aiohttp.ClientSession() as session:
        # Создаем список для записи данных
        data = []

        # Обрабатываем каждую ссылку
        for link in links:
            # Находимся на каждой странице
            page_data = await handle_page(session, link.strip())

            # Сохраняем изображения
            await save_images(page_data['image_urls'], page_data['sku'])

            # Добавляем данные в список
            data.append(page_data)

    # Сохраняем данные в файл JSON
    with open('data.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

    # Выводим полученные данные
    print(data)


if __name__ == "__main__":
    asyncio.run(main())
