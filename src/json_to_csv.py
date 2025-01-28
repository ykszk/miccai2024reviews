import paper_info
from loguru import logger
import pandas as pd

def main():
    db_path = paper_info.default_db_path()

    list_info = paper_info.PaperInfo.load_from_db(db_path)
    category_info = paper_info.CategorizedPaper.load_from_db(db_path)
    category_dict = {info.id: info.category for info in category_info}
    logger.info(f"{len(list_info)} papers loaded from db")
    # %%
    rows = []
    for info in list_info:
        logger.debug(info.url)
        row = {
            "id": info.id,
            "title": info.title,
            "url": info.url,
            "authors": "|".join(info.authors),
            "topics": "|".join(info.topics),
            "category": category_dict.get(info.id, None),
        }
        for i, review in enumerate(info.reviews):
            row[f"review_score_{i}"] = review.confidence_score()
            row[f'post_rebuttal_score_{i}'] = review.post_rebuttal_confidence_score()
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv("data/papers.csv", index=False)

if __name__=="__main__":
    main()