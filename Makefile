.PHONY: backend-lint backend-format backend-test frontend-lint frontend-test frontend-build frontend-e2e test

backend-lint:
	cd backend && ruff check .

backend-format:
	cd backend && ruff format .

backend-test:
	cd backend && pytest -q

frontend-lint:
	cd frontend && npm run lint

frontend-test:
	cd frontend && npm run test

frontend-build:
	cd frontend && npm run build

frontend-e2e:
	cd frontend && npm run test:e2e

test: backend-lint backend-test frontend-lint frontend-test frontend-build frontend-e2e
