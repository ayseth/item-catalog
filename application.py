from flask import Flask, render_template, request, redirect, url_for, \
    flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from flask import session as login_session
from flask import make_response
import flask_whooshalchemy as wa

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import random
import string
import json
import httplib2
import requests



CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web'
                                                                ]['client_id']
APPLICATION_NAME = 'Games Catalog Application'
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///catalog2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=True
app.config['WHOOSH_BASE']='whoosh'

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False)
    picture =db.Column(db.String(250))
    role = db.Column(db.String(250))

class catalog(db.Model):
	__searchable__ = ['title', 'content', 'category']

	id= db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(250), nullable=False)
	content = db.Column(db.String(1000))
	category = db.Column(db.String(250))
	picture = db.Column(db.String(1000))
	link = db.Column(db.String(1000))
	cover_pic = db.Column(db.String(1000))
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	# user = db.relationship(db.User)

	@property
	def serialize(self):
		return {
		'id' : self.id,
		'title' : self.title,
		'content' : self.content,
		'category' : self.category,
		'picture' : self.picture,
		
		}

class comments(db.Model):
    __tablename__='comments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    catalog_id = db.Column(db.Integer, db.ForeignKey('catalog.id'))
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False)
    content = db.Column(db.String(1000))
    status = db.Column(db.String(250))
    picture =db.Column(db.String(250))


wa.whoosh_index(app, catalog)

@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase +
                    string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'
                                            ), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data

    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json',
                                             scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = \
            make_response(json.dumps('''Failed to upgrade the
                                        authorization code.'''), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials.access_token
    url = \
        'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' \
        % access_token
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = \
            make_response(json.dumps('''Token's user ID doesn't
                          match given user ID.'''), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        response = \
            make_response(json.dumps('''Token's client ID does not
                                     match app's.'''), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = \
            make_response(json.dumps('''Current user is
                            already connected.'''), 200)
        response.headers['Content-Type'] = 'application/json'

    login_session['provider'] = 'google'
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += \
        ''' " style = "width: 300px;
        height: 300px;border-radius: 150px;
        -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '''
    flash('you are now logged in as %s' % login_session['username'])
    print 'done!'
    return output


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    db.session.add(newUser)
    db.session.commit()
    user = User.query.filter_by(email=login_session['email'
                                                             ]).one()
    return user.id


def getUserInfo(user_id):
    user = User.query.filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = User.query.filter_by(email=email).one()
        return user.id
    except:
        return None




@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        response = \
            make_response(json.dumps('Current user not connected.'),
                          401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
        % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['gplus_id']
        del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = redirect(url_for('showcatalog'))
        flash('You are now logged out.')
        return response
    else:
        response = \
            make_response(json.dumps('Failed to revoke token for given user.',
                                     400))
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/catalogs/JSON')
def showcatalogJSON():
    catalogJ = catalog.query.order_by('catalog.id desc').all()
    return jsonify(catalog=[i.serialize for i in catalogJ])

@app.route('/')
@app.route('/catalog/')
def showcatalog():
    catalogs = catalog.query.order_by('catalog.id desc').limit(5)
    if 'username' not in login_session:
        return render_template('publiccatalog.html', catalogs=catalogs)
    else:
        return render_template('catalog.html', catalogs=catalogs)

@app.route('/catalog/new', methods=['GET', 'POST'])
def newitem():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = catalog(
            title=request.form['title'],
            content=request.form['content'],
            category=request.form['category'],
            picture=request.form['picture'],
            link=request.form['link'],
            cover_pic=request.form['cover_pic'],
            user_id=login_session['user_id'],
            )
        db.session.add(newItem)
        db.session.commit()
        flash('Item added successfully')
        return redirect(url_for('showcatalog'))
    else:
        return render_template('additem.html')

@app.route('/catalog/<string:catalog_category>/items')
def showitems(catalog_category):
    listcatalogs = catalog.query.filter_by(category=catalog_category)
    count = catalog.query.filter_by(category=catalog_category
                                                      ).count()
    if 'username' not in login_session:
        return render_template('publicshowitems.html',
                               listcatalogs=listcatalogs, count=count,
                               title=catalog_category)
    else:
        return render_template('showitems.html',
                               listcatalogs=listcatalogs, count=count,
                               title=catalog_category)

@app.route('/catalog/<string:catalog_category>/<string:catalog_title>')
def showitem(catalog_category, catalog_title):
    displaycontent = \
        catalog.query.filter_by(title=catalog_title).one()
    creator = getUserInfo(displaycontent.user_id)
    comment = comments.query.filter_by(catalog_id=displaycontent.id).all()
    if 'username' not in login_session or creator.id \
            != login_session['user_id']:
        return render_template('publicshowitem.html',
                               displaycontent=displaycontent,
                               creator=creator, comment=comment)
    else:
        return render_template('showitem.html',
                               displaycontent=displaycontent,
                               creator=creator, comment=comment)

@app.route('/catalog/<string:catalog_title>/edit', methods=['GET',
           'POST'])
def edititem(catalog_title):
    editItem = \
        catalog.query.filter_by(title=catalog_title).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editItem.user_id != login_session['user_id']:
        return '''<script>function myFunction()
        {alert('You are not authorized to edit this.
        Please create your own item in order to edit.');}
        </script><body onload='myFunction()''>'''
    if request.method == 'POST':
        if request.form['title']:
            editItem.title = request.form['title']
        if request.form['content']:
            editItem.content = request.form['content']
        if request.form['category']:
            editItem.category = request.form['category']
        if request.form['picture']:
            editItem.picture = request.form['picture']
        if request.form['link']:
            editItem.link = request.form['link']
        if request.form['cover_pic']:
            editItem.cover_pic = request.form['cover_pic']
        db.session.add(editItem)
        db.session.commit()
        flash('Item edited successfully')
        return redirect(url_for('showitems',
                        catalog_category=editItem.category))
    else:
        return render_template('Edititem.html',
                               catalog_title=catalog_title,
                               item=editItem)

@app.route('/catalog/<string:catalog_title>/delete', methods=['GET',
           'POST'])
def deleteitem(catalog_title):
    deleteItem = \
        catalog.query.filter_by(title=catalog_title).one()
    if 'username' not in login_session:
        return redirect('/login')
    if deleteItem.user_id != login_session['user_id']:
        return '''<script>function myFunction()
        {alert('You are not authorized to delete this item.
        Please create your own item in order to delete.');}
        </script><body onload='myFunction()''>'''
    if request.method == 'POST':
        db.session.delete(deleteItem)
        db.session.commit()
        flash('Item deleted successfully')
        return redirect(url_for('showitems',
                        catalog_category=deleteItem.category))
    else:
        return render_template('deleteitem.html',
                               catalog_title=catalog_title,
                               item=deleteItem)
@app.route('/search')
@app.route('/catalog/search')
def search():
    catalogs = catalog.query.whoosh_search(request.args.get('query')).all()
    if 'username' not in login_session:
        return redirect('/login')
    return render_template('search.html', catalogs=catalogs)


@app.route('/catalog/<string:catalog_category>/<string:catalog_title>/comment', methods=['GET', 'POST'])
def newcomment(catalog_category, catalog_title):
    if 'username' not in login_session:
        return redirect('/login')
    cat_id=catalog.query.filter_by(title=catalog_title).one()
    if request.method == 'POST':
        newcomment = comments(
            user_id=login_session['user_id'],
            catalog_id=cat_id.id,
            name=login_session['username'],
            email=login_session['email'],
            content=request.form['comment'],
            status="unapproved",
            picture=login_session['picture']
            )
        db.session.add(newcomment)
        db.session.commit()
        flash('Comment added')
        return redirect(url_for('showitem', catalog_category=cat_id.category, catalog_title=cat_id.title))
    else:
        return render_template('addcomment.html')


@app.route('/admin/<int:user_id>')
def admin(user_id):
    if 'username' not in login_session:
       return redirect('/login')
    user = User.query.filter_by(id=user_id).one()
    if user.role !='admin':
        return "You're not authorized to view this page"
    return "welcome admin"


if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)