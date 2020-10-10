from flask import g, Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanici kayit formu
class RegisterForm(Form):
    name = StringField("Isminizi ve Soyiminizi giriniz", validators=[validators.Length(min=4, max=25)])
    username = StringField("Kullanici adinizi giriniz", validators=[validators.Length(min=5, max=30)])
    email = StringField("Emailinizi giriniz", validators=[validators.Email(message="Gecerli bir Email giriniz...")])
    password = PasswordField("Parolanizi giriniz", validators=[
        validators.DataRequired(message="lutfen Bir Parola Belirleyin"), 
        validators.EqualTo(fieldname="confirm", message="Parolaniz uyusmuyor")])
    confirm = PasswordField("Parolanizi yeniden giriniz")
    
# Girish formu
class LoginForm(Form):
        username = StringField("Kullanici adinizi giriniz")
        password = PasswordField("Parolanizi giriniz")

# kullanici Giris Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayi goruntulemek icin lutfen giish yapin","danger")
            return redirect(url_for("index"))
    return decorated_function



app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


#MySqle baglamaq
app.config["MYSQL_HOST"] = '127.0.0.1'
app.config["MYSQL_USER"] = 'root'
app.config["MYSQL_PASSWORD"] = ''
app.config["MYSQL_DB"] = 'ybblog'
app.config["MYSQL_CURSORCLASS"] = 'DictCursor'


mysql = MySQL(app)



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s"

    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles =  cursor.fetchall()
        return render_template("dashboard.html",articles = articles)

    else:
        return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("index"))


@app.route("/login", methods = ["GET","POST"])
def login():

    form = LoginForm(request.form)

    if request.method == "POST"and form.validate():
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        
        sorgu = "Select * From users where username = %s"
        
        result = cursor.execute(sorgu,(username,))
        
        if result > 0 :
            data = cursor.fetchone()
            real_password = data["password"]

            if sha256_crypt.verify(password_entered,real_password):
                flash("Basariyla giris yaptiniz", "success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Kullanici adi ve ya parola yalnis","danger")
                return redirect(url_for("login"))

        else:
            flash("Kullanici adi ve ya parola yalnis","danger")
            return redirect(url_for("login"))
    else:
        return render_template('login.html',form=form)




@app.route("/register", methods = ["GET","POST"])
def register():

    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "INSERT INTO users(name, email, username, password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,email,username,password))

        mysql.connection.commit()

        cursor.close()

        flash(message="Basariyla kayit oldunuz", category="success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)



#Makale Ekleme

@app.route("/addarticle", methods = ["GET", "POST"])
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
 
        cursor = mysql.connection.cursor()

        sorgu = "INSERT INTO articles(title, author, content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title, session["username"], content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale basriyla eklendi", "success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html",form=form)

#Makale form
class ArticleForm(Form):
    title = StringField("Makale basligi", validators=[validators.Length(min=5,max=100)])
    content = TextAreaField("Makale icerigi", validators=[validators.Length(min=10)])


#Makale Sayfasi
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")


# Detay sayfasi

@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where id = %s"

    result = cursor.execute(sorgu,(id,))

    if(result > 0):
        article = cursor.fetchone()
        return render_template("article.html", article = article)
        
    else:
        return render_template("article.html")


#Makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "select * from articles where author=%s and id = %s"

    result = cursor.execute(sorgu,(session["username"], id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s" 
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("Aradiginiz makale bulunamadi ve ya bu isleme yetkiniz yok")
        return redirect(url_for("index"))


#Makale Guncelleme

@app.route("/edit/<string:id>", methods = ["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        sorgu = "select * from articles where id = %s and author = %s"

        result = cursor.execute(sorgu, (id, session["username"]))

        if result == 0:
            flash("Boyle bir makale yok ve ya isleme yetkiniz yok", "danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("update.html",form = form)


    else:
        #POST request
        form = ArticleForm(request.form)
        Ntitle = form.title.data
        Ncontent = form.content.data
 
        cursor = mysql.connection.cursor()

        sorgu = "update articles set title = %s, content = %s where id = %s"
        cursor.execute(sorgu,(Ntitle, Ncontent, id))
        mysql.connection.commit()
        cursor.close()
        flash("Makale basriyla Guncellendi", "success")
        return redirect(url_for("dashboard"))

# Arama Url
@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "Select * From articles where title like '%" + keyword + "%'"
        
        result = cursor.execute(sorgu)
        if result == 0:
            flash("Aranan Uygun mekale bulunamadi", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)



if __name__ == "__main__":
    app.run(debug=True)
