import os
from re import template
import re 
from requests import api

from sqlalchemy.sql.elements import not_
from sqlalchemy.sql.expression import null, update
from helpers import login_required

from flask import Flask, session, redirect, render_template, request, url_for, flash, jsonify
from flask_session import Session
from sqlalchemy import create_engine, select
from sqlalchemy.orm import query, scoped_session, sessionmaker
from flask_bcrypt import Bcrypt, check_password_hash,generate_password_hash
import requests
import json
import secrets
 
app = Flask(__name__)

# Check for environment variable
if not os.getenv("DB_URL"):
    raise RuntimeError("DB_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DB_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Secrets Key
secret_key = secrets.token_hex(16)
app.config["SECRET_KEY"] = secret_key

@app.route("/")
@login_required
def index():

    # Almacenamos en unas variables la ejecucion de la base de datos
    book = db.execute("SELECT * FROM books LIMIT 50")
    
    # Retornamos al usuario a la pagina con los datos generado anteriormente
    return render_template("index.html", book=book)

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():

    if request.method == 'GET':

        # Almacenamos en una variable el libro que deseamos buscar
        busqueda_values = request.args.get("search_book")
        
        if all(text.isspace() for text in busqueda_values):
            info_message = "😔 Hey! parece que no has puesto bien el libro que deseas buscar"
            flash(info_message, "info")
            return redirect("/")

        # Aplicamos un formateo y lo almacenamos en otra variable
        Busqueda = "%{}%".format(busqueda_values.strip())
        
        # Buscamos el libro en la base de datos mediante el input de la barra de navegacion
        book = db.execute("SELECT * FROM books WHERE isbn ILIKE :isbn OR title ILIKE :title OR autor ILIKE :autor OR year ILIKE :year", {"isbn":Busqueda, "title":Busqueda, "autor":Busqueda, "year":Busqueda}).fetchall()

        # Validamos si el libro se encuentra en nuestra base de datos en caso de no encotrarse redirecionamos a un error 404
        if not book:
            info_message = "😔 Lo siento el libro que deseas buscar no se encuentra disponible"
            flash(info_message, "info")
            return redirect("/")

        return render_template("index.html", book=book)
        
    
@app.route("/login", methods=["GET", "POST"])
def login():

    # Olvida cualquier id_user
    session.clear()

    # Metodo POST
    if request.method == 'POST':

        # Almacenamos en la variable los datos obtenido en el formulario
        username = request.form.get("username")
        password = request.form.get("password")

        rows = db.execute("SELECT * FROM usuarios WHERE username = :username", {"username":username}).fetchone()

        # Validacion del Usuario si existe en la base de datos 
        if db.execute("SELECT * FROM usuarios WHERE username = :username", {"username":username}).rowcount == 0:
            error_message = "😕 Hey! parece que tuvimos un problema con el nombre de usuario"
            flash(error_message, "error")
            return render_template("login.html") 

        # Validacion de la contraseña al iniciar sesion
        if not check_password_hash(rows[2], password):
            error_message = "😕 Hey! parece que tuvimos un problema con tu contraseña"
            flash(error_message, "error")
            return render_template("login.html")

        session["user_id"] = rows[0]
        session['username'] = rows[1]

        # Redirecionamos a la pagina principal
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    # Olvida cualquier id_user
    session.clear()

    # Metodo POST
    if request.method == 'POST':

        # Almacenamos en la variable los datos obtenido en el formulario
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        checkpassword = request.form.get("checkpassword").strip()
        


        # Validamos en la base de datos de que no haya otro usuario con el mismo nombre
        if db.execute("SELECT * FROM usuarios WHERE username = :username", {"username":username}).rowcount == 1:
            error_message = "😕 Hey! el nombre de usuario que deseas ocupar ya fue registrado"
            flash(error_message, "error")
            return render_template("register.html")

        # Chequeamos si la contraseña son iguales
        if password != checkpassword:
            error_message = "😕 Hey! parece que tuvimos un problema con tu verificacion de contraseña vuelve a intentar"
            flash(error_message, "error")
            return render_template("register.html")
        
        # Validamos de que no guarde el nombre del usuario y contraseña con espacios
        elif all(text.isspace() for text in username):
            info_message = "😕 Hey! parece que no has puesto bien el nombre de usuario"
            flash(info_message, "info")
            return render_template("register.html")

        elif all(text.isspace() for text in password):
            info_message = "😕 Hey! parece que no has puesto bien la contraseña"
            flash(info_message, "info")
            return render_template("register.html")
        # Encriptamos la contraseña y decodificamos la cadena
        hash = generate_password_hash(password).decode('utf-8')

        # Ingresamos los datos en la base de datos
        db.execute("INSERT INTO usuarios (username, password) VALUES (:username, :password)", {"username":username, "password":hash})
        db.commit()
        
        # Redirecionamos a la pagina Login
        return redirect("/login")
        
    else:
        # En caso de falla volvemos a cargar la pagina registro
        return render_template("register.html")

@app.route("/logout")
def logout():

    # Olvida cualquier id_user
    session.clear()

    # Redirecionamos al usuario a la pagina iniciar sesion
    return redirect("/login")

@app.route("/BooksPages/<isbn>", methods=["POST", "GET"])
@login_required
def books(isbn):  
    # Metodo GET
    if request.method == 'GET':
        
        paracetamol = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn}).fetchall()
        
        # Sacar el comentario de la base de datos
        datos = db.execute("SELECT id_books FROM books WHERE isbn = :isbn", {"isbn":isbn})      
        id = datos.fetchone()[0]
        Reviews = db.execute("SELECT usuarios.username, reviews.comentario, reviews.puntaje FROM reviews INNER JOIN usuarios ON usuarios.id_user = reviews.id_user WHERE id_books = :id_books",{"id_books": id})
        
        api_consulta = requests.get(f"https://www.googleapis.com/books/v1/volumes?q=+isbn:{isbn}&maxResult=1")

        if api_consulta.status_code != 200:
            return "error al cargar la API" 

        if api_consulta.status_code == 200:

            api_resultados = api_consulta.json()

            if api_resultados['totalItems'] == 0:
                return render_template("404.html")
            else: 
                API = api_resultados['items'][0]['volumeInfo']

                # Verifico si existe ['description'] en la API
                if ('description' in API):
                    
                    descripcion = API['description']

                    try:
                        print("LA DESCRIPCION ES: " + descripcion)

                    except:
                        print("La Descripcion no existe en este libro")
                        descripcion="Not description"
                else:
                    descripcion="Not description"

                # Verifico si existe ['averageRating'] en la API
                if ('averageRating' in API):
                    
                    rating = API['averageRating']

                    try:
                        print("EL RATING ES: " + str(rating))

                    except:
                        print("El Rating no existe en este libro")
                        rating="Not rating"
                else:
                    rating="Not rating"

                # Verifico si existe ['publishedDate'] en la API
                if ('publishedDate' in API):
                    
                    publicacion = API['publishedDate']

                    try:
                        print("El libro fue publicado: " + publicacion)

                    except:
                        print("El no tiene fecha de publicado")
                        publicacion="Not date published date"
                else:
                    publicacion="Not date published date"

                # Verifico si existe ['thumbnail'] en la API
                if (('imageLinks' or 'thumbnail') in API):
                    
                    imagen = API['imageLinks']['thumbnail']

                    try:
                        print("Imagen del libro es: " + str(imagen))
                    except:
                        print("No Contiene Thumnail")
                        imagen = "../static/img/no-imagen.jpeg"
                else:
                    imagen = "../static/img/no-imagen.jpeg"

                # Verifico si existe ['ratingsCount'] en la API
                if ('ratingsCount' in API):
                    Contador = API['ratingsCount']
                    try:
                        print("El contador de rating es de: " + str(Contador))
                    except:
                        print("No tiene contador de rating")
                        Contador = "Not ratings Count"
                else:       
                    Contador = "Not ratings Count"

                # Verifico si existe ['pageCount'] en la API
                if ('pageCount' in API):
                    Pagina = API['pageCount']
                    try:
                        print("El libro tiene: "+ str(Pagina) +" pagina")
                    except:
                        print("No tiene contador de pagina")
                        Pagina = "Not Page Count"
                else:
                    Pagina = "Not page count"

                # Verifico si existe ['publisher'] en la API
                if ('publisher' in API):
                    editor = API['publisher']
                    try:
                        print("EL EDITOR DEL LIBRE ES: " + editor)
                    except:
                        print("NOT PUBLISHER")
                        editor =  "Not published"
                else:
                    editor = "Not publisher"

            return render_template("books.html", imagen=imagen, descripcion = descripcion, parecetamol = paracetamol, rating = rating, publicacion = publicacion, Contador = Contador, Pagina=Pagina, Reviews = Reviews, editor = editor)
    else:

        # Almacenamos en la variable los datos obtenido en la caja de comentario y puntaje
        texto =  request.form.get("comentarios").strip()
        puntos = request.form.get("rate")

        # Seleccionamos los datos del libro mediante el ISBN Seleccionado
        datos = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn})

        id = datos.fetchone()[4]
        id_u = session["user_id"]

        checkrows = db.execute("SELECT * FROM reviews WHERE id_user = :id_user AND id_books = :id_books", {"id_user":id_u, "id_books":id})
        
        # Si el campo del comentario y puntaje esta vacio no puede enviar una reseñar
        if not (texto and puntos):
            info_message = "🤡 Hey! parece que no has añadido un puntaje al libro"
            flash(info_message, "info")
            return redirect("/BooksPages/"+str(isbn))
        elif all(text.isspace() for text in texto):
            info_message = "🤡 Hey! parece que no has agregado un comentario"
            flash(info_message, "info")
            return redirect("/BooksPages/"+str(isbn))

        # Si el usuario no tiene una reseña en un libro, lo guardamos
        if checkrows.rowcount == 0:
            db.execute("INSERT INTO reviews (id_books, id_user ,comentario, puntaje) VALUES (:id_books, :id_user, :comentario, :puntaje)", {"id_books":id ,"id_user":id_u ,"comentario":texto, "puntaje":puntos})
            db.commit()
            success_message = "😃 Hey! hemos guardado tu comentario"
            flash(success_message, "success")
            return redirect("/BooksPages/"+str(isbn))
        
        else:
            # Si el usuario ya tiene una review, lo actualizamos
            id_reviews = db.execute("SELECT id_review FROM reviews WHERE id_user = :id_user AND id_books = :id_books", {"id_user":id_u, "id_books":id})
            id_reviews = id_reviews.fetchone()[0]   
            actualizar = db.execute("UPDATE reviews SET comentario = :comentario, puntaje = :puntaje WHERE id_review = :id_review",{"comentario":texto, "puntaje":puntos ,"id_review":id_reviews})
            db.commit()
            success_message = "😃 Hey! hemos actualizado tu comentario"
            flash(success_message, "success")
            return redirect("/BooksPages/"+str(isbn))

@app.route("/api/<isbn>", methods=["GET"])
def my_api(isbn):

    # Seleccionamos los datos especifico de nuestra base de datos mediante de la ISBN
    myAPI = db.execute("SELECT books.id_books, books.title, books.autor, books.year, books.isbn, AVG(reviews.puntaje) AS average, COUNT(reviews.id_review) AS contador FROM books LEFT JOIN reviews ON books.id_books = reviews.id_books WHERE isbn = :isbn GROUP BY books.id_books", {"isbn": isbn}).fetchone()

    if not myAPI:
        return render_template("404.html")


    # Si myAPI.average no es null me retorna valor flotante
    if myAPI.average is not None:
       average = float(myAPI.average)
    else:
        # si MyAPI.average es null me retorna valor null
        average = myAPI.average

    return jsonify(Titulo = myAPI.title, Autor = myAPI.autor ,Año = myAPI.year, ISBN = myAPI.isbn, recuento_de_media = average, recuento_de_reseñas = myAPI.contador)

@app.route("/404", methods=["GET", "POST"])
@app.errorhandler(404)
def book_not_found(error):
    # establecemos el estado 404
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(debug=True)
    bcrypt = Bcrypt(app)