import os
import errno
import logging
from fastapi import FastAPI
from lorem_text import lorem
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class LoremIpsumRequest(BaseModel):
    paragraphs:  int
    words: int


class LoremIpsumResponse(BaseModel):
    paragraphs:  Optional[List[str]] = []


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


def generate_loremipsum(paragraphs: int,  words: int) -> list:
    """
    :param paragraphs: number of paragraphs to be generated
    :param words: number of paragraph words to generate
    :return: List of generated paragraphs
    """

    return list(map(lambda x: lorem.words(words), range(paragraphs)))


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


logger = set_logger(log_name='server', log_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log'))
app = FastAPI(title='Lorem ipsum API')


@app.post('/lorem', response_model=LoremIpsumResponse)
async def loremipsum(req_param: LoremIpsumRequest):
    logger.info(f"[SERVER] Incoming request: Paragraphs - {req_param.paragraphs} Words - {req_param.words}")
    result = generate_loremipsum(req_param.paragraphs, req_param.words)
    return {"paragraphs": result}
