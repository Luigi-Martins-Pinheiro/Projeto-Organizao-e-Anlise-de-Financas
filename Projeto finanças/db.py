import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="Finanças",
        user="postgres",
        password="20070918"
    )




