

## Prerequisites

- Python 3.11 or higher
- Poetry (dependency management)
- Redis (for caching and Celery)
- PostgreSQL (database)

## Getting Started

1. Clone the repository:

2. Install dependencies using Poetry:

poetry install

3. Set up the environment variables:

Create a `.env` file in the project root and add the following variables:

OPENAI_API_KEY=your_openai_api_key
GROQ_API_KEY=your_groq_api_key
ELEVEN_API_KEY=your_eleven_api_key
SUPABASE_API_URL=your_supabase_api_url
SUPABASE_API_KEY=your_supabase_api_key
SUPABASE_URL=your_supabase_url
MISTRAL_API_KEY=your_mistral_api_key
HUGGINGFACE_API_TOKEN=your_huggingface_api_token
POSTGRES_DB=your_postgres_database
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=your_postgres_port
REDIS_HOST=your_redis_host
REDIS_PORT=your_redis_port
REDIS_PASSWORD=your_redis_password


Replace the placeholders with your actual API keys and database credentials.

4. Run database migrations:



5. Start the development server:
python manage.py runserver_plus --cert-file /tmp/cert
export DJANGO_SETTINGS_MODULE=hellogpt.settings.dev
python manage.py runserver --settings=hellogpt.settings.dev

6. Start the Celery worker:

poetry run celery -A hellogpt worker --loglevel=info


The Django development server should now be running at `http://localhost:8000`, and Celery should be running in the background.

## Running Tests

To run the test suite, use the following command:



poetry run pytest