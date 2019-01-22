#!/usr/bin/python


from flask import Flask, render_template, request, redirect, url_for, \
    flash, jsonify
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database_setup import Base, catalog, User
from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web'
                                                                ]['client_id']
APPLICATION_NAME = 'Games Catalog Application'

engine = create_engine('sqlite:///catalog.db?check_same_thread=False')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


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
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email'
                                                             ]).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
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


# @app.route('/disconnect')
# def disconnect():
#     if 'provider' in login_session:
#         if login_session['provider'] == 'google':
#             gdisconnect()

#         # if login_session['provider'] == 'facebook':
#         #     fbdisconnect()
#         #     del login_session['facebook_id']

#         del login_session['user_id']
#         del login_session['provider']
#         flash("You have successfully been logged out.")
#         return redirect(url_for('showcatalog'))
#     else:
#         flash("You were not logged in")
#         return redirect(url_for('showcatalog'))

@app.route('/catalogs/JSON')
def showcatalogJSON():
    catalogJ = session.query(catalog).order_by('catalog.id desc').all()
    return jsonify(catalog=[i.serialize for i in catalogJ])


@app.route('/')
@app.route('/catalog/')
def showcatalog():
    catalogs = session.query(catalog).order_by('catalog.id desc'
                                               ).limit(5)
    if 'username' not in login_session:
        return render_template('publiccatalog.html', catalogs=catalogs)
    else:
        return render_template('catalog.html', catalogs=catalogs)
    # return "displays Latest items"


@app.route('/catalog/<string:catalog_category>/items')
def showitems(catalog_category):
    listcatalogs = session.query(catalog).filter_by(category=catalog_category)
    count = session.query(catalog.category).filter_by(category=catalog_category
                                                      ).count()
    if 'username' not in login_session:
        return render_template('publicshowitems.html',
                               listcatalogs=listcatalogs, count=count,
                               title=catalog_category)
    else:
        return render_template('showitems.html',
                               listcatalogs=listcatalogs, count=count,
                               title=catalog_category)
        # return "this show items for category %s" % category_category


@app.route('/catalog/new', methods=['GET', 'POST'])
def newitem():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = catalog(
            title=request.form['title'],
            description=request.form['description'],
            category=request.form['category'],
            picture=request.form['picture'],
            link=request.form['link'],
            cover_pic=request.form['cover_pic'],
            user_id=login_session['user_id'],
            )
        session.add(newItem)
        try:
        	session.commit()
        except:
        	session.rollback()
        flash('Item added successfully')
        return redirect(url_for('showcatalog'))
    else:
        return render_template('additem.html')
    # return "this is to add a new item"


@app.route('/catalog/<string:catalog_category>/<string:catalog_title>')
def showitem(catalog_category, catalog_title):
    displaycontent = \
        session.query(catalog).filter_by(title=catalog_title).one()
    creator = getUserInfo(displaycontent.user_id)
    if 'username' not in login_session or creator.id \
            != login_session['user_id']:
        return render_template('publicshowitem.html',
                               displaycontent=displaycontent,
                               creator=creator)
    else:
        return render_template('showitem.html',
                               displaycontent=displaycontent,
                               creator=creator)
        # return "this shows item for %s title" % catalog_title


@app.route('/catalog/<string:catalog_title>/edit', methods=['GET',
           'POST'])
def edititem(catalog_title):
    editItem = \
        session.query(catalog).filter_by(title=catalog_title).one()
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
        if request.form['description']:
            editItem.description = request.form['description']
        if request.form['category']:
            editItem.category = request.form['category']
        if request.form['picture']:
            editItem.picture = request.form['picture']
        if request.form['link']:
            editItem.link = request.form['link']
        if request.form['cover_pic']:
            editItem.cover_pic = request.form['cover_pic']
        session.add(editItem)
        try:
        	session.commit()
        except:
        	session.rollback()
        flash('Item edited successfully')
        return redirect(url_for('showitems',
                        catalog_category=editItem.category))
    else:
        return render_template('Edititem.html',
                               catalog_title=catalog_title,
                               item=editItem)
        # return "this will edit item %s " % catalog_title


@app.route('/catalog/<string:catalog_title>/delete', methods=['GET',
           'POST'])
def deleteitem(catalog_title):
    deleteItem = \
        session.query(catalog).filter_by(title=catalog_title).one()
    if 'username' not in login_session:
        return redirect('/login')
    if deleteItem.user_id != login_session['user_id']:
        return '''<script>function myFunction()
        {alert('You are not authorized to delete this item.
        Please create your own item in order to delete.');}
        </script><body onload='myFunction()''>'''
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        flash('Item deleted successfully')
        return redirect(url_for('showitems',
                        catalog_category=deleteItem.category))
    else:
        return render_template('deleteitem.html',
                               catalog_title=catalog_title,
                               item=deleteItem)

    # return "this will delete item %s" % catalog_title

@app.route('/search')
def searchitem():
    return "this will show search items"

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
