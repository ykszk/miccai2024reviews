# %%
from downloader import DBCachedDownload
from loguru import logger
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, RootModel
from typing import List, Optional
import re
import sqlite3

ROOT_URL = "https://papers.miccai.org"
PAPER_LIST_URL = ROOT_URL + "/miccai-2024/"


class ListedPaper(BaseModel):
    title: str
    authors: List[str]
    urls: List[str]

    @classmethod
    def list_papers(cls, source: str, url: str) -> List["ListedPaper"]:
        url_root = "/".join(url.split("/")[:3])
        logger.info(f"Root URL: {url_root}")
        soup = BeautifulSoup(source, "lxml")
        assert soup.title is not None and soup.title.text == "MICCAI 2024 - Open Access"
        container = soup.select_one("div.container-posts")
        assert container is not None
        listed_papers = []
        for li in container.select("ul > div > li"):
            lp = cls.from_tag(li, url_root)
            logger.info(f"Found paper: {lp.title}")
            listed_papers.append(lp)
        return listed_papers

    @classmethod
    def from_tag(cls, li: Tag, url_root: str) -> "ListedPaper":
        title = li.select_one("b").text  # type: ignore
        ul = li.select_one("ul")
        assert ul is not None
        # authors is the first li
        ul_lis = ul.find_all("li")
        authors = ul_lis[0]
        authors = [e.text for e in authors.find_all("a")]
        # url is the second li
        links = ul_lis[1]
        urls = []
        for e in links.findChildren("a", recursive=False):
            if "href" in e.attrs:
                urls.append(url_root + e["href"])
        assert len(urls) == 2
        return cls(title=title, authors=authors, urls=urls)

    def pdf_url(self) -> str:
        return self.urls[0]

    def info_url(self) -> str:
        return self.urls[1]


class Review(RootModel):
    root: List[str]

    def confidence(self) -> str:
        return self.root[-3]

    def _extract_confidence_score(self, confidence: str) -> int:
        pattern = r"\((\d+)\)"
        match = re.search(pattern, confidence)
        assert match is not None, f"Confidence score not found: {confidence}"
        return int(match.group(1))

    def confidence_score(self) -> int:
        return self._extract_confidence_score(self.confidence())

    def post_rebuttal_confidence(self) -> str:
        return self.root[-2]

    def post_rebuttal_confidence_score(self) -> Optional[int]:
        c = self.post_rebuttal_confidence()
        if c == "N/A":
            return None
        return self._extract_confidence_score(c)


class MetaReview(RootModel):
    root: List[str]


def extract_paper_id(url: str) -> int:
    match = re.search(r"Paper(\d+)", url)
    assert match is not None
    return int(match.group(1))

class PaperInfo(BaseModel):
    url: str
    id: int
    title: str
    authors: List[str]
    reviews: List[Review]
    meta_reviews: List[MetaReview]
    topics: List[str]

    @classmethod
    def from_source(cls, source: str, url: str) -> "PaperInfo":
        paper_id = extract_paper_id(url)

        soup = BeautifulSoup(source, "lxml")
        container = soup.select_one("article.container-post")
        assert container is not None
        title = container.select_one("h1 b")
        assert title is not None
        title = title.text
        authors = container.select_one("div.post-tags")
        assert authors is not None
        authors = [a.text.strip() for a in authors.find_all("a")]
        # reviews
        reviews = []
        for review_id in range(1, 10):
            review = container.select_one(f"h3#review-{review_id}")
            if review is None:
                break
            answers = []
            for ns in review.next_siblings:
                if ns.name in ['h2','h3','hr]']:
                    break
                if ns.name == 'ul':
                    ul = ns
                    assert isinstance(ul, Tag)
                    answers.extend([a.text.strip() for a in ul.select("li > blockquote")])
            assert len(answers) == 12, (url, ul)
            reviews.append(Review(answers))
        assert len(reviews) > 0
        # meta reviews
        meta_reviews = []
        for meta_review_id in range(1, 10):
            meta_review = container.select_one(f"h2#meta-review-{meta_review_id}")
            if meta_review is None:
                break
            ul = meta_review.find_next_sibling("ul")
            assert isinstance(ul, Tag)
            answers = [a.text.strip() for a in ul.select("li > blockquote")]
            meta_reviews.append(MetaReview(answers))
        # early accepted paper has no meta-review
        topics = [a.text.strip() for a in soup.select("div.post-categories > a")]
        paper_info = PaperInfo(
            url=url,
            id=paper_id,
            title=title,
            authors=authors,
            reviews=reviews,
            meta_reviews=meta_reviews,
            topics=topics,
        )
        return paper_info

    @classmethod
    def save_in_db(cls, info_list: List["PaperInfo"], db_path: str):
        # saev PaperInfo as json in sqlite3 using id as primary key
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS papers (id INTEGER PRIMARY KEY, json TEXT)"
            )
            data_to_insert = [(info.id, info.model_dump_json()) for info in info_list]
            conn.executemany(
                "REPLACE INTO papers (id, json) VALUES (?, ?)",
                data_to_insert,
            )

    @classmethod
    def load_from_db(cls, db_path: str) -> List["PaperInfo"]:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT json FROM papers")
            data = cursor.fetchall()
            return [PaperInfo.model_validate_json(d[0]) for d in data]


def default_db_path() -> str:
    return str(Path(__file__).parent / "../data/data.sqlite")

def main():
    db_path = default_db_path()
    downloader = DBCachedDownload(db_path)
    content = downloader.download(PAPER_LIST_URL).decode("utf-8")

    listed_papers = ListedPaper.list_papers(content, PAPER_LIST_URL)
    logger.info(f"{len(listed_papers)} papers found")

    list_info = []
    for listed_papr in listed_papers:
        logger.info(listed_papr.title)
        info_url = listed_papr.info_url()

        content = downloader.download(info_url).decode("utf-8")
        paper_info = PaperInfo.from_source(content, info_url)

        list_info.append(paper_info)
    PaperInfo.save_in_db(list_info, db_path)

    logger.info('Fetching category information')
    category_url = 'https://papers.miccai.org/miccai-2024/categories/'
    content = downloader.download(category_url).decode("utf-8")
    papers = CategorizedPaper.list_papers(content)
    CategorizedPaper.save_in_db(papers, default_db_path())

class CategorizedPaper(BaseModel):
    category: str
    title: str
    id: int

    @classmethod
    def save_in_db(cls, paper_list: List["CategorizedPaper"], db_path: str):
        # saev PaperInfo as json in sqlite3 using id as primary key
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS categorized_papers (id INTEGER PRIMARY KEY, json TEXT)"
            )
            data_to_insert = [(info.id, info.model_dump_json()) for info in paper_list]
            conn.executemany(
                "REPLACE INTO categorized_papers (id, json) VALUES (?, ?)",
                data_to_insert,
            )

    @classmethod
    def load_from_db(cls, db_path: str) -> List["CategorizedPaper"]:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT json FROM categorized_papers")
            data = cursor.fetchall()
            return [CategorizedPaper.model_validate_json(d[0]) for d in data]
        
    @classmethod
    def list_papers(cls, source: str) -> List["CategorizedPaper"]:
        soup = BeautifulSoup(source, 'lxml')
        article = soup.select_one('article')
        assert article is not None
        actual_article = article.select_one('class')
        papers = []
        for e in actual_article.find_all(recursive=False):
            if e.name == 'h3':
                category = e.text.strip()
                logger.info(category)
            if e.name == 'div':
                a = e.select_one('a')
                paper_title = a.text.strip()
                link = a.attrs['href']
                paper_id = extract_paper_id(link)
                papers.append(CategorizedPaper(category=category, title=paper_title, id=paper_id))
        return papers

if __name__=="__main__":
    main()