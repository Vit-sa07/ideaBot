import psycopg2

from config import DATABASE_URL

connection = psycopg2.connect(DATABASE_URL)

cursor = connection.cursor()
cursor.execute("""
    CREATE TABLE test (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    text TEXT,
    hashtags TEXT[]
);



""")
connection.commit()
cursor.close()
connection.close()
