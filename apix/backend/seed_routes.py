import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, user='apix', password='apix_secret', dbname='apix_db')
cur = conn.cursor()
cur.execute("INSERT INTO routes (route_code, origin, destination, weight, active) VALUES ('DEL-BOM','DEL','BOM',0.5, true),('DEL-BLR','DEL','BLR',0.3, true),('BOM-BLR','BOM','BLR',0.2, true)")
conn.commit()
conn.close()
print('Routes seeded')
