.PHONY: server migration migrate shell routes lint commit

server:
	poetry run python manage.py runserver

migration:
	poetry run python manage.py makemigrations

migrate:
	poetry run python manage.py migrate

shell:
	poetry run python manage.py shell_plus --print-sql

routes:
	poetry run python manage.py show_urls

lint:
	poetry run pre-commit run --all-files

commit:
	poetry run cz commit