import re
from email.utils import parsedate_to_datetime
from hashlib import md5
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests import exceptions, get, head

from itee_hub import LOGGER, data_dir, db

TAG = "util"


def get_year_from_txt(text: str):
    """
    Extracts a four digit year from the given text.

    Searches for a four digit year in various formats in the provided text, 
    Format examples: '2024 April Exam', '2019S_FE.pdf', 'IPApril2012.zip'.

    Args:
        text (str): The input text from which to extract the year.

    Returns:
        str or None: Returns a four-digit year as a string if found;
                     otherwise, None if no valid year is found.
    """

    patter_0 = re.findall(r"(\d{2})?(\d{4})", text)
    pattern_1 = re.search(r"(\d{4}|(?:(IP|FE|AP)\d{4}))", text, re.IGNORECASE)
    if patter_0:
        for match in patter_0:
            for txt in match:
                if len(txt) == 4:
                    return txt

    if pattern_1:
        return pattern_1.group(1)

    return None


def get_info_from_link(link: str) -> list:
    """
    Extracts information from the provided link.

    Retrieves relevant data such as the type of 
    - content (question or result), 
    - the level (exam level), 
    - the country, 
    - the year 
    from the given link using regex. 

    Args:
        link (str): The input link from which to extract information.

    Returns:
        dict: A dictionary containing the extracted information, which may include:
            - "link" (str): The original link.
            - "type" (str): The type of content ("question" or "result").
            - "level" (str): The exam level derived from the link.
            - "country" (str): The country extracted from the link, if available.
            - "year" (str): The year extracted from the link, if available.

            The dictionary may contain fewer keys if certain information is not found.
    """

    data = {}
    data["link"] = link

    ques_cat_pattern_0 = re.search(r"pastexamqa/([^/]+)/", link)
    ques_cat_pattern_1 = re.search(r"(IP|FE|AP)", link)
    country = re.search(r"all-passers-information/([^/]+)/", link)
    year_text = get_year_from_txt(link)

    if ques_cat_pattern_0:
        data["type"] = "question"
        data["level"] = ques_cat_pattern_0.group(1).lower()
    elif ques_cat_pattern_1:
        data["type"] = "result"
        data["level"] = ques_cat_pattern_1.group(1).lower()
    else:
        LOGGER.warning("Unable to find question type from: %s", link)

    if country:
        data["country"] = country.group(1)
    else:
        if "pastexamqa" not in link:
            LOGGER.warning("Unable to find country from: %s", link)

    if year_text:
        data["year"] = year_text
    else:
        LOGGER.warning("Unable to find year from: %s", link)

    return data


def get_file_path_from_link_info(data):
    """
    Constructs the file path from the provided link information.

    Generates a file path based on the extracted information from a link including
    - the year
    - type of content (result or question), 
    - the country
    
    It also checks if the constructed path exists.

    Args:
        data (dict): A dictionary containing link information, which must include:
            - "link" (str): The original link.
            - "year" (str): The year associated with the link.
            - "type" (str): The type of content ("result" or "question").
            - "country" (str): The country associated with the link.

    Returns:
        Path or None: Returns a `Path` object representing the file path if it exists; 
        otherwise, returns None.
    """

    file_name = Path(urlparse(data["link"]).path).name

    path_prefix = data["year"]
    if data["type"] == "result":
        path_prefix += f"/results/{data['country']}_{file_name}"
    elif data["type"] == "question":
        path_prefix += f"/questions/{file_name}"
    else:
        LOGGER.warning("Invalid folder type was given: %s", data["type"])

    file_path = data_dir / path_prefix
    if file_path.exists():
        return file_path

    LOGGER.info("Unable to get file path for: %s", data["link"])
    return None


def get_web_page_soup(link):
    try:
        resp = get(link)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except exceptions.BaseHTTPError as err:
        LOGGER.error("[%s] failed to get response from: %s. reason: %s", TAG, link, err)
        return
    except Exception as err:
        LOGGER.error(
            "[%s] unknown error occurred while getting response from: %s. reason: %s",
            TAG,
            link,
            err,
        )
        return

    return BeautifulSoup(resp.content, "lxml")


def is_file_changed(link: str):
    """
    Checks if the file at the specified link has changed since the last recorded modification time.

    To retrieve the "Last-Modified" header, a HEAD request is made to the given URL then it
    compares the retrieved timestamp with the last known modification time stored in the database, 
    and returns a boolean indicating whether the file has changed.

    Args:
        link (str): The URL of the file to check.

    Returns:
        bool: Returns True if the file has changed;
        otherwise, returns False.
    """

    resp = head(link)
    resp.raise_for_status()
    last_modified = parsedate_to_datetime(resp.headers.get("last-modified"))
    last_modified = int(last_modified.timestamp())
    return db.get_file(link, last_modified, "") is True


def download(
    path_suffix: str,
    link: str,
    year_month: str,
    file_name_suffix: str = None,
    refresh_file: bool = False,
):
    """
    Downloads a file from the specified link and saves it to the provided path.

    Construct a file path based on the provided suffix and link. 

    If the file already exists, it checks for changes based on the last modified 
    timestamp and the file's md5 hash. 
    If changes are detected or if `refresh_file` is set to True, the file is re-downloaded.

    Args:
        path_suffix (str): The path suffix where the file will be saved.
        link (str): The URL of the file to download.
        year_month (str): The year and month associated with the file.
        file_name_suffix (str, optional): An optional suffix to prepend to the file name. 
                                           Defaults to None.
        refresh_file (bool, optional): If True, forces re-download of the file, 
                                        even if it already exists. Defaults to False.

    Returns:
        None
    """

    file_name = Path(urlparse(link).path).name
    if file_name_suffix:
        file_name = file_name_suffix + "_" + file_name

    file_path = data_dir / path_suffix
    file_path.mkdir(parents=True, exist_ok=True)
    file_path = file_path / file_name

    if file_path.exists():
        if not refresh_file:
            LOGGER.info("[%s] already downloaded: %s, skipping", TAG, file_name)
            return

        LOGGER.info("[%s] already downloaded: %s, checking changes", TAG, file_name)
        if is_file_changed(link):
            LOGGER.info("[%s] changes detected: %s, downloading.", TAG, file_name)
        else:
            LOGGER.info("[%s] no changes detected: %s", TAG, file_name)
            return

    resp = get(link)
    resp.raise_for_status()

    last_modified = parsedate_to_datetime(resp.headers.get("last-modified"))
    last_modified = int(last_modified.timestamp())

    file_hash = md5(resp.content).hexdigest()

    LOGGER.info("[%s] downloaded: %s", TAG, file_name)

    with file_path.open("wb") as f:
        f.write(resp.content)

    db.add_file(link, last_modified, year_month, file_hash)
