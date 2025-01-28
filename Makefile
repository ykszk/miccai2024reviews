all: create_html

init:
	[ -f data/data.sqlite ] || zstd -d data/data.sqlite.zst -o data/data.sqlite && touch src/paper_info.py

fetch_paper_info: data/data.sqlite

create_csv: data/papers.csv

create_html: data/index.html

clear_json_data:
	sqlite3 data/data.sqlite "DROP TABLE IF EXISTS papers;" && sqlite3 data/data.sqlite "DROP TABLE IF EXISTS categorized_papers;"

archive:
	zstd -9 data/data.sqlite -o data/data.sqlite.zst

clean:
	rm -f data/data.sqlite data/papers.csv data/index.html

deploy: deploy/index.html

data/data.sqlite: src/paper_info.py
	LOGURU_LEVEL=INFO python3 src/paper_info.py

data/papers.csv: data/data.sqlite src/json_to_csv.py
	LOGURU_LEVEL=INFO python3 src/json_to_csv.py

data/index.html: data/papers.csv src/notebook.py
	jupytext --to ipynb --output - --update-metadata '{"title":"MICCAI 2024 Review Analysis"}' ./src/notebook.py | jupyter-nbconvert --stdin --to html --execute --no-input --template pj --output data/index.html

deploy/index.html: data/index.html
	mkdir -p deploy && cp data/index.html deploy/index.html
