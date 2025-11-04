env:
	cp env.dev .env

up-log:
	make env
	docker compose up -d
	docker compose logs -f --tail 500

down:
	docker compose down

restart:
	make down
	make up-log
