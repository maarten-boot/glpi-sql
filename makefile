# makefile: tab=tab, ts=4

PYTHON		:=	python3.12
PL_LINTERS	:=	eradicate,mccabe,pycodestyle,pyflakes,pylint
LINE_LENGTH	:= 120
PY_FILES 	:= *.py
PL_IGNORE	:= C0114,C0116,C0115,C0103,W0719,R0904,W0231,E203

# Doc strings missing: C0114,C0116,C0115,C0103
# W0719
# R0904
# W0231
# E203

all: clean prep run

clean:
	rm -f 1 2 out

prep: black pylama

black:
	black \
		--line-length $(LINE_LENGTH) \
		$(PY_FILES)

pylama:
	pylama \
		--max-line-length $(LINE_LENGTH) \
		--linters "${PL_LINTERS}" \
		--ignore "${PL_IGNORE}" \
		$(PY_FILES)

mypy: clean
	mypy \
		--strict \
		--no-incremental $(PY_FILES)

run: parse_create_table_mariadb

parse_create_table_mariadb:
	$(PYTHON)  ./$@.py 2>$@.2 | tee $@.1

