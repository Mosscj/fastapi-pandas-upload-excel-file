
import sqlite3

# Path to your SQLite database file
db_file = "vehicle.db"

# Connect to the SQLite database
conn = sqlite3.connect(db_file)

cursor = conn.cursor()

# Example query to fetch all data from a specific table (replace 'your_table_name' with the actual table name)
cursor.execute("SELECT * FROM vehicles")

# Fetch all rows from the query result
rows = cursor.fetchall()

# Print the data
for row in rows:
    print(row)

# Close the connection
print(db_file)
conn.close()