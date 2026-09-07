.PHONY: up down build logs migrate seed test acceptance lint shell

up:        ## Start the full stack (build + migrate + seed happen automatically)
	docker compose up --build

down:      ## Stop and remove containers
	docker compose down

logs:      ## Tail API logs
	docker compose logs -f api

migrate:   ## Run a new migration inside the running container
	docker compose exec api alembic upgrade head

revision:  ## Create a new Alembic revision — usage: make revision m="add foo"
	docker compose exec api alembic revision --autogenerate -m "$(m)"

seed:      ## Re-run the baseline data seed
	docker compose exec api python -m app.seed

test:      ## Run the fast local test suite
	pytest tests/ -v -m "not acceptance"

acceptance: ## Run the end-to-end release gate against the running stack
	pytest tests/acceptance/ -v -m acceptance

lint:      ## Run ruff
	ruff check app/ tests/

shell:     ## Open a shell in the running API container
	docker compose exec api /bin/sh
