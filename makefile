
FILES	=: parse_create_table_mariadb.py


all: prep run

prep: black

black:
	black *.py

run: parse_create_table_mariadb

parse-glpi-db:
	python3 ./parse-glpi-db.py 2>2 | tee out

parse_create_table_mariadb:
	python3  ./parse_create_table_mariadb.py 2>2 | tee 1

