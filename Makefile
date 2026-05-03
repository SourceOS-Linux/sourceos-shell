.PHONY: validate smoke up down

validate:
	@echo "==> Validating workspace layout..."
	@test -d services/docd          || (echo "FAIL: services/docd missing"         && exit 1)
	@test -d services/pdf-secure    || (echo "FAIL: services/pdf-secure missing"   && exit 1)
	@test -d apps/pdf-viewer-demo   || (echo "FAIL: apps/pdf-viewer-demo missing"  && exit 1)
	@test -d content/draft          || (echo "FAIL: content/draft missing"         && exit 1)
	@test -d content/derived        || (echo "FAIL: content/derived missing"       && exit 1)
	@test -d content/reports        || (echo "FAIL: content/reports missing"       && exit 1)
	@test -f services/docd/src/derive.js              || (echo "FAIL: services/docd/src/derive.js missing"              && exit 1)
	@test -f services/pdf-secure/src/sign-validate.js || (echo "FAIL: services/pdf-secure/src/sign-validate.js missing" && exit 1)
	@test -f apps/pdf-viewer-demo/src/smoke.js        || (echo "FAIL: apps/pdf-viewer-demo/src/smoke.js missing"        && exit 1)
	@echo "PASS: validate"

smoke:
	@echo "==> Running smoke tests..."
	@echo "--- services/docd ---"
	node services/docd/src/derive.js
	@echo "--- services/pdf-secure ---"
	node services/pdf-secure/src/sign-validate.js
	@echo "--- apps/pdf-viewer-demo ---"
	node apps/pdf-viewer-demo/src/smoke.js
	@echo "PASS: smoke"

up:
	docker compose -f infra/compose/docker-compose.yml up --build

down:
	docker compose -f infra/compose/docker-compose.yml down -v

