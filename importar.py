#Libreria
import psycopg2
import csv

#Varible que almacena credenciales 
#Datos de importancia las credenciales pueden variar cierto tiempo
db_host  =  ""
db_name = "d1laovdg348joa"
db_user = "oejpzdxrxukxkt"
db_pass  = ""
db_port  = ""

#Conexion de la base datos Postgres
conexion = psycopg2.connect(dbname=db_name, user=db_user, password=db_pass, host=db_host, port=db_port)

cur = conexion.cursor()


# Fase 1: Comando para crear la tabla
#cur.execute("CREATE TABLE Books(isbn text PRIMARY KEY, title text, autor text, year text, id_books SERIAL);")

# FASE 2: IMPORTA EL ARCHIVO CSV
#Importar el Archivo CSV
#with open('books.csv', 'r') as f:
 #   reader = csv.reader(f)
  #  next(reader)

   # for row in reader:
    #    cur.execute("INSERT INTO Books VALUES (%s, %s, %s, %s)",
     #   row
      #  )

#Metodo para confirmar la transacción
conexion.commit()

#Cierre de Cursor y Conexion de la base de datos
cur.close()
conexion.close()





