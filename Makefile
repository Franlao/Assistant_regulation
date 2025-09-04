.PHONY: test test-unit test-integration test-coverage install-dev lint format clean

# Installation des dépendances de développement
install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-mock pytest-cov black flake8 mypy

# Tests unitaires rapides
test-unit:
	pytest tests/ -m "unit" -v

# Tests d'intégration (plus lents)
test-integration:
	pytest tests/ -m "integration" -v

# Tous les tests
test:
	pytest tests/ -v

# Tests avec couverture de code
test-coverage:
	pytest tests/ --cov=assistant_regulation --cov-report=html --cov-report=term

# Formatage du code
format:
	black assistant_regulation/ tests/ config/ --line-length 100

# Vérification du style
lint:
	flake8 assistant_regulation/ tests/ config/ --max-line-length=100
	mypy assistant_regulation/ --ignore-missing-imports

# Nettoyage des fichiers temporaires
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov/ .coverage

# Lancer l'application
run:
	streamlit run app.py

# Tests rapides pour le développement (tests fiables uniquement)
test-quick:
	pytest tests/test_simple.py tests/test_config.py -x -v --tb=short

# Tests complets (avec imports complexes)
test-all:
	pytest tests/ -x -v --tb=short