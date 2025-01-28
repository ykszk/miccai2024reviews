
fetch_paper_info: data/data.sqlite

create_csv: data/papers.csv

clear_json_data:
	sqlite3 data/data.sqlite "DROP TABLE IF EXISTS paper;"

data/data.sqlite: src/paper_info.py
	LOGURU_LEVEL=INFO python3 src/paper_info.py

data/papers.csv: data/data.sqlite src/json_to_csv.py
	LOGURU_LEVEL=INFO python3 src/json_to_csv.py

index.html: data/papers.csv src/notebook.py
	jupytext --to ipynb --output - --update-metadata '{"title":"MICCAI 2024 Review Analysis"}' ./src/notebook.py | jupyter-nbconvert --stdin --to html --execute --no-input --template pj --output index.html