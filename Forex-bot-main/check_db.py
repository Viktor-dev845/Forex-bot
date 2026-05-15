import sqlite3
import pandas as pd

def check_db():
    try:
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        for table in tables:
            table_name = table[0]
            print(f"\n--- {table_name} (last 5 rows) ---")
            try:
                df = pd.read_sql_query(f"SELECT * FROM \"{table_name}\" LIMIT 5", conn)
                print(df)
            except Exception as e:
                print(f"Error reading {table_name}: {e}")
                
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    check_db()
