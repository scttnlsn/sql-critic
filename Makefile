lint:
	black --check .
	isort --check .
	
check:
	mypy sqlcritic

format:
	black .
	isort .

publish:
	python -m build
	twine check dist/*
	twine upload dist/*

.PHONY: lint check format publish