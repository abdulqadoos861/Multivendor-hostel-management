import sqlite3
import os

# Path to your SQLite database
db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if the roomassignment table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coustom_admin_roomassignment';")
table_exists = cursor.fetchone()

if table_exists:
    print("Table 'coustom_admin_roomassignment' exists in the database.")
    
    # Get the table structure
    cursor.execute("PRAGMA table_info(coustom_admin_roomassignment);")
    columns = cursor.fetchall()
    print("\nTable structure:")
    for col in columns:
        print(f"Column: {col[1]}, Type: {col[2]}, Not Null: {bool(col[3])}, Default: {col[4]}, Primary Key: {bool(col[5])}")
    
    # Check if there are any records
    cursor.execute("SELECT COUNT(*) FROM coustom_admin_roomassignment;")
    count = cursor.fetchone()[0]
    print(f"\nNumber of records: {count}")
    
    # Show sample data if any
    if count > 0:
        cursor.execute("SELECT * FROM coustom_admin_roomassignment LIMIT 5;")
        print("\nSample data:")
        for row in cursor.fetchall():
            print(row)
else:
    print("Table 'coustom_admin_roomassignment' does not exist in the database.")

# Close the connection
conn.close()
