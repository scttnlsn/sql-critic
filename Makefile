format:
	black .
	isort .

publish:
	python -m build
	twine check dist/*
	twine upload dist/*

.PHONY: format publish