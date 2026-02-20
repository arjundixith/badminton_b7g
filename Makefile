.PHONY: backend frontend seed test

backend:
	cd backend && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

seed:
	cd backend && python seed.py

test:
	cd backend && pytest
