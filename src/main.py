#%%
from downloader import DBCachedDownload
from logzero import logger
ROOT_URL = 'https://papers.miccai.org'
PAPER_LIST_URL = ROOT_URL + '/miccai-2024/'
# %%
from pathlib import Path
db_path = Path(__file__).parent / '../data.sqlite'
downloader = DBCachedDownload(str(db_path))
content = downloader.download(PAPER_LIST_URL).decode('utf-8')
# %%
from bs4 import BeautifulSoup, Tag
soup = BeautifulSoup(content, 'lxml')
assert soup.title is not None and soup.title.text == 'MICCAI 2024 - Open Access'
# %%
list_papers = soup.select_one('div.container-posts ul')
assert list_papers is not None
# %%
from pydantic import BaseModel
from typing import List
import re

class ListedPaper(BaseModel):
    title: str
    authors: List[str]
    urls: List[str]

    @classmethod
    def list_papers(cls, source: str, url: str) -> List['ListedPaper']:
        url_root = '/'.join(url.split('/')[:3])
        logger.info(f'Root URL: {url_root}')
        soup = BeautifulSoup(source, 'lxml')
        assert soup.title is not None and soup.title.text == 'MICCAI 2024 - Open Access'
        container = soup.select_one('div.container-posts')
        assert container is not None
        listed_papers = []
        for li in container.select('ul > div > li'):
            lp = cls.from_tag(li, url_root)
            logger.info(f'Found paper: {lp.title}')
            listed_papers.append(lp)
        return listed_papers

    @classmethod
    def from_tag(cls, li: Tag, url_root: str) -> 'ListedPaper':
        title = li.select_one('b').text # type: ignore
        ul = li.select_one('ul')
        assert ul is not None
        # authors is the first li
        ul_lis = ul.find_all('li')
        authors = ul_lis[0]
        authors = [e.text for e in authors.find_all('a')]
        # url is the second li
        links = ul_lis[1]
        urls = []
        for e in links.findChildren('a', recursive=False):
            if 'href' in e.attrs:
                urls.append(url_root + e['href'])
        assert len(urls) == 2
        return cls(title=title, authors=authors, urls=urls)
    
    def pdf_url(self) -> str:
        return self.urls[0]
    
    def info_url(self) -> str:
        return self.urls[1]

listed_papers = ListedPaper.list_papers(content, PAPER_LIST_URL)
print(len(listed_papers), 'papers found')

# %%

class Review(BaseModel):
    answers: List[str]

    def confidence(self) -> str:
        return self.answers[-3]
    
    def _extract_confidence_score(self, confidence: str) -> int:
        pattern = r'\((\d+)\)'
        match = re.search(pattern, confidence)
        assert match is not None
        return int(match.group(1))
    
    def confidence_score(self) -> int:
        return self._extract_confidence_score(self.confidence())
    
    def post_rebuttal_confidence(self) -> str:
        return self.answers[-2]
    
    def post_rebuttal_confidence_score(self) -> int:
        return self._extract_confidence_score(self.post_rebuttal_confidence())

class MetaReview(BaseModel):
    answers: List[str]

class PaperInfo(BaseModel):
    url: str
    id: int
    title: str
    authors: List[str]
    reviews: List[Review]
    meta_reviews: List[MetaReview]
    topics: List[str]

    @classmethod
    def from_source(cls, source: str, url: str) -> 'PaperInfo':
        match = re.search(r'Paper(\d+)', url)
        assert match is not None
        paper_id = int(match.group(1))

        soup = BeautifulSoup(source, 'lxml')
        container = soup.select_one('article.container-post')
        assert container is not None
        title = container.select_one('h1 b')
        assert title is not None
        title = title.text
        authors = container.select_one('div.post-tags')
        assert authors is not None
        authors = [a.text.strip() for a in authors.find_all('a')]
        # reviews
        reviews = []
        for review_id in range(1, 10):
            review = container.select_one(f'h3#review-{review_id}')
            if review is None:
                break
            ul = review.find_next_sibling('ul')
            assert isinstance(ul, Tag)
            answers = [a.text for a in ul.select('blockquote > p')]
            reviews.append(Review(answers=answers))
        assert len(reviews) > 0
        # meta reviews
        meta_reviews = []
        for meta_review_id in range(1, 10):
            meta_review = container.select_one(f'h2#meta-review-{meta_review_id}')
            if meta_review is None:
                break
            ul = meta_review.find_next_sibling('ul')
            assert isinstance(ul, Tag)
            answers = [a.text for a in ul.select('blockquote > p')]
            meta_reviews.append(MetaReview(answers=answers))
        assert len(meta_reviews) > 0
        topics = [a.text.strip() for a in soup.select('div.post-categories > a')]
        paper_info = PaperInfo(url=info_url, id=paper_id, title=title, authors=authors, reviews=reviews, meta_reviews=meta_reviews, topics=topics)
        return paper_info


for listed_papr in listed_papers:
    print(listed_papr.title)
    info_url = listed_papr.info_url()

    content = downloader.download(info_url).decode('utf-8')
    paper_info = PaperInfo.from_source(content, info_url)

    break