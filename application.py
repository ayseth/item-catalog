from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database_setup import Base, catalog

app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db?check_same_thread=False')
Base.metadata.bind = engine

DBSession = sessionmaker(bind= engine)
session = DBSession()

@app.route('/catalogs/JSON')
def showcatalogJSON():
	catalog=session.query(catalog).order_by("catalog.id desc").all()
	return jsonify(catalog=[i.serialize for i in catalog])
	
@app.route('/')
@app.route('/catalog/')
def showcatalog():
	catalogs=session.query(catalog).order_by("catalog.id desc").limit(10)
	return render_template('catalog.html', catalogs = catalogs)
	# return "displays Latest items"

@app.route('/catalog/<string:catalog_category>/items')
def showitems(catalog_category):
	listcatalogs=session.query(catalog).filter_by(category=catalog_category)
	count=session.query(catalog.category).filter_by(category=catalog_category).count()
	return render_template('showitems.html', listcatalogs = listcatalogs, count=count, title=catalog_category)
	# return "this show items for category %s" % category_category

@app.route('/catalog/new', methods=['GET', 'POST'])
def newitem():
	if request.method == 'POST':
		newItem = catalog(title=request.form['title'], description=request.form['description'], category=request.form['category'], picture=request.form['picture'], link=request.form['link'], cover_pic=request.form['cover_pic'])
		session.add(newItem)
		session.commit()
		flash("Item added successfully")
		return redirect(url_for('showcatalog'))
	else:
		return render_template('additem.html')
	# return "this is to add a new item"

@app.route('/catalog/<string:catalog_category>/<string:catalog_title>')
def showitem(catalog_category, catalog_title):
	displaycontent=session.query(catalog).filter_by(title=catalog_title).all()
	return render_template('showitem.html', displaycontent = displaycontent)
	# return "this shows item for %s title" % catalog_title

@app.route('/catalog/<string:catalog_title>/edit', methods=['GET', 'POST'])
def edititem(catalog_title):
	editItem=session.query(catalog).filter_by(title=catalog_title).one()
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
		session.commit()
		flash("Item edited successfully")
		return redirect(url_for('showitems', catalog_category = editItem.category))
	else:
		return render_template('Edititem.html', catalog_title=catalog_title, item=editItem)
	# return "this will edit item %s " % catalog_title

@app.route('/catalog/<string:catalog_title>/delete', methods=['GET', 'POST'])
def deleteitem(catalog_title):
	deleteItem=session.query(catalog).filter_by(title=catalog_title).one()
	if request.method == 'POST':
		session.delete(deleteItem)
		session.commit()
		flash("Item deleted successfully")
		return redirect(url_for('showitems', catalog_category=deleteItem.category))
	else:
		return render_template('deleteitem.html', catalog_title=catalog_title, item=deleteItem )
	# return "this will delete item %s" % catalog_title


if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)
