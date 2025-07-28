-- Initialize pgvector extension
-- This script runs automatically when the PostgreSQL container starts for the first time

-- Create the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a database for the application if it doesn't exist
-- The default database 'postgres' will be used as specified in the connection string

-- Grant necessary permissions to the docker user
GRANT ALL PRIVILEGES ON DATABASE postgres TO docker;

-- Display installed extensions
SELECT * FROM pg_extension WHERE extname = 'vector';
