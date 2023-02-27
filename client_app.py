import os
import errno
import logging
import aiohttp
import asyncio
import argparse
import aiosqlite
from typing import Optional
from datetime import datetime


logger = None


def mkdir(path: str) -> str:
    """
    :param path: create a directory <path> recursively
    :return : Full path to the created directory, otherwise - None
    """
    created_path = path
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            created_path = None
    finally:
        return created_path


def set_logger(log_name: str, log_folder: str) -> Optional[logging.StreamHandler]:
    """
    :param log_name: logger name
    :param log_folder: Path to log folder
    :return:  Logger object (or  None if no Logger object has been created)
    """
    log = None
    try:
        log_dir = mkdir(log_folder)
        if log_dir:
            log = logging.getLogger(log_name)
            file_log_name = os.path.join(log_dir,  f'{log_name}_{datetime.now().strftime("%Y%m%d%H%M%S")}.log')
            file_log = logging.FileHandler(file_log_name)
            console_log = logging.StreamHandler()
            console_format = logging.Formatter('%(levelname)s - %(message)s')
            file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_log.setFormatter(console_format)
            file_log.setFormatter(file_format)
            log.addHandler(console_log)
            log.addHandler(file_log)
            log.setLevel(logging.INFO)
        else:
            raise Exception(f"Directory '{log_folder}' for logs has not been created")
    except Exception as exc:
        print(f"[set_logger] {exc}")
    finally:
        return log


async def request_text(endpoint: str, text_num: int, paragraphs_num: int, words_num: int):
    """
    :param endpoint: Server URL
    :param text_num: Request number (for statistic purpose)
    :param paragraphs_num: Number of requested paragraphs
    :param words_num: Number of words per paragraph
    :return: tuple
             0 - '' if  the request was successful, otherwise error message
             1 - dict with following structure {'text_num':<request number>, 'paragraphs':['paragraph text', ..]} 
    """
    result_data = {'num': text_num}
    error = ''
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json={"paragraphs": paragraphs_num, "words": words_num}) as response:
                if response.status == 200:
                    data = await response.json()
                    result_data.update(data)
                    logger.info(
                        f"[CLIENT] Text number: {text_num} paragraphs: {paragraphs_num} "
                        f"words: {words_num} Status: {response.status}"
                    )
                else:
                    raise f"[CLIENT] [{response.status}] {await response.text()}"
    except Exception as exc:
        error = str(exc)
        logger.error(f"[CLIENT] Text number: {text_num} paragraphs: {paragraphs_num} words: {words_num} - Error:{exc}")
    finally:
        return error, result_data


async def main(endpoint: str, database_path: str, texts_num: int, paragraphs_num: int, words_num: int) -> None:
    """
    :param endpoint: Server URL
    :param database_path: Path to folder with SQLLite database
    :param texts_num: Number of requested texts
    :param paragraphs_num: Number of paragraphs per text
    :param words_num: Number of words per paragraph
    :return:
    """
    db = None
    try:
        db = await aiosqlite.connect(os.path.join(database_path, 'loremipsum.db'))
        await db.execute(
            'CREATE TABLE IF NOT EXISTS loremipsum(id INTEGER PRIMARY KEY, '
            'text_num INTEGER, paragraph_num INTEGER, text TEXT, stamp INTEGER)'
        )
        tasks = [request_text(endpoint, text_num, paragraphs_num, words_num) for text_num in range(texts_num)]
        for task in asyncio.as_completed(tasks):
            error, data = await task
            if error:
                logger.error(f"Request {data['num']}: {error}")
            else:
                logger.info(f"[CLIENT] Add request {data['num']} to db")
                timestamp = int(datetime.utcnow().timestamp() * 1000)
                data_to_db = [
                    (data['num'], p_num, p_text, timestamp) for p_num, p_text in enumerate(data['paragraphs'], 1)
                ]
                await db.executemany(
                    "INSERT INTO loremipsum(text_num, paragraph_num, text, stamp) VALUES(?, ?, ?, ?)", data_to_db
                )
                await db.commit()
    except Exception as exc:
        logger.error(f"Error:{exc}")
    else:
        async with db.execute("SELECT stamp FROM loremipsum GROUP BY stamp") as cursor_s:
            async for stamp in cursor_s:
                logger.info(f"\nText unique Id: {stamp[0]}")
                async with db.execute(
                        f"SELECT text_num, paragraph_num, text FROM loremipsum "
                        f"WHERE stamp={stamp[0]} "
                        f"ORDER BY paragraph_num") as cursor_t:
                    async for row in cursor_t:
                        logger.info(f"{row[0]}:{row[1]} {row[2]}")
    finally:
        if db:
            await db.close()


if __name__ == "__main__":
    args = argparse.ArgumentParser(description='Lorem ipsum client')
    args.add_argument('--host', help='Host', required=True)
    args.add_argument('--port', help='Port', required=True, type=int)
    args.add_argument('-t', '--texts', help="number of texts to generate", type=int, default=100)
    args.add_argument('-w', '--words', help="number of words per paragraph to generate", type=int, default=100)
    args.add_argument('-p', '--paragraphs', help="number of paragraphs per text to generate", type=int, default=10)
    logger = set_logger(log_name='client', log_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log'))
    try:
        db_path = mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db'))
        url = f"http://{args.parse_args().host}:{args.parse_args().port}/lorem"
        asyncio.run(main(url, db_path, args.parse_args().texts, args.parse_args().paragraphs, args.parse_args().words))
    except Exception as exc:
        logger.error(str(exc))
