Run tests (Python 3.10+):

- Install deps: `pip install -e . python-dotenv`
- Run all tests: `python -m unittest discover -s tests -p 'test_*.py' -v`
- Live tests (optional): set `CLOUDCRUISE_API_KEY` and `CLOUDCRUISE_ENCRYPTION_KEY` (or use `tests/.env`), then `python -m unittest tests/test_live_staging.py -v`

Run a specific test:

- Single file: `python -m unittest tests/test_webhook.py -v`
- Single method: `python -m unittest tests.test_webhook.TestWebhook.test_verify_signature_ok -v`
