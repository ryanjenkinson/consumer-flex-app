.PHONY: setup
setup:
	poetry install
	poetry run pre-commit install

dfs-app:
	poetry run streamlit run consumer_flex_app/demand_flexibility_service/app.py
