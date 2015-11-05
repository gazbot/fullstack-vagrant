from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catalog, Category, Item
# OAuth imports
# from flask import session as login_session
# import random, string

app = Flask(__name__)

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


"""
Endpoints
  ** catalog  **
/
/catalogs/
/catalogs/new/
/<catalog_name>/
/<catalog_name>/edit/
/<catalog_name>/delete/

  ** category **
/<catalog_name>/categories/
/<catalog_name>/category/new/
/<catalog_name>/<category_name>/
/<catalog_name>/<category_name>/edit/
/<catalog_name>/<category_name>/delete/

  ** item **
/<catalog_name>/items/
/<catalog_name>/items/add/
/<catalog_name>/items/<item_name>/
/<catalog_name>/items/<item_name>/edit/
/<catalog_name>/items/<item_name>/delete/

"""


"""
Items Section
"""
@app.route('/<catalog_name>/items/<item_name>/')
def showItem(catalog_name, item_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    item = session.query(Item).filter_by(catalog_id=catalog.catalog_id, name=item_name).one()
    return render_template('itemDisplay.html', catalog=catalog, item=item)
    
 
# Edit the named item
@app.route('/<catalog_name>/items/<item_name>/edit/', methods=['GET', 'POST'])
def editItem(catalog_name, item_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    categories = session.query(Category).filter_by(catalog_id=catalog.catalog_id).all()
    item = session.query(Item).filter_by(catalog_id=catalog.catalog_id, name=item_name).one()
    itemCategory = session.query(Category).filter_by(catalog_id=catalog.catalog_id, category_id=item.category_id).one()
    if request.method == 'POST':
        editItemCategory = session.query(Category).filter_by(name=request.form['category']).one()
        item.name = request.form['name']
        item.description = request.form['description']
        item.category_id = editItemCategory.category_id
        return redirect(url_for('showItem', catalog_name = catalog.name, item_name=item.name))
    else:
        return render_template('itemEdit.html', catalog=catalog, categories=categories, item=item, itemCategory=itemCategory)  
  
  
# Deletes the named item, displays confirmation page before removal 
@app.route('/<catalog_name>/items/<item_name>/delete/', methods=['GET', 'POST'])
def deleteItem(catalog_name, item_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    itemToDelete = session.query(Item).filter_by(catalog_id=catalog.catalog_id, name=item_name).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('listItems', catalog_name=catalog.name))
    else:
        return render_template('itemDelete.html', catalog=catalog, item=itemToDelete)


# Creates a new item
@app.route('/<catalog_name>/items/new/', methods=['GET', 'POST'])
def newItem(catalog_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    categories = session.query(Category).filter_by(catalog_id=catalog.catalog_id).all()
    if request.method == 'POST':
        category = session.query(Category).filter_by(name=request.form['category']).one()
        item = Item(name=request.form['name'], description=request.form['description'], category_id=category.category_id, catalog_id=catalog.catalog_id)
        session.add(item)
        session.commit()
        return redirect(url_for('listItems', catalog_name=catalog.name))
    else:
        return render_template('itemNew.html', catalog=catalog, categories=categories)
    

# List items, supports certain query parameters,
# list orderBy / page / pageSize 
@app.route('/<catalog_name>/items/')
def listItems(catalog_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    items = session.query(Item).filter_by(catalog_id=catalog.catalog_id).all()
    return render_template('itemList.html', catalog=catalog, items=items)

 

"""
Catalog Section
"""
@app.route('/')
@app.route('/catalogs/')
def showCatalogs():
    catalogs = session.query(Catalog).all()
    return render_template('catalogList.html', catalogs=catalogs, catalogActive=1)


@app.route('/catalogs/new/', methods=['GET', 'POST'])
def newCatalog():
    if request.method == 'POST':
        newCatalog = Catalog(name=request.form['name'], description=request.form['description'])
        session.add(newCatalog)
        session.commit()
        return redirect(url_for('showCatalogs'))
    else:
        return render_template('catalogNew.html')


@app.route('/<string:catalog_name>/')
def showCatalog(catalog_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    categories = session.query(Category).filter_by(catalog_id=catalog.catalog_id).all()
    items = session.query(Item).filter_by(catalog_id=catalog.catalog_id).all()
    return render_template('catalogDisplay.html', catalog=catalog, categories=categories, items=items, catalogActive=1)


@app.route('/<string:catalog_name>/edit/', methods=['GET', 'POST'])
def editCatalog(catalog_name):
    editedCatalog = session.query(Catalog).filter_by(name=catalog_name).one()
    if request.method == 'POST':
        if request.form['name']:
            editedCatalog.name = request.form['name']
            editedCatalog.description = request.form['description']
            return redirect(url_for('showCatalog', catalog_name = editedCatalog.name))
    else:
        return render_template('catalogEdit.html', catalog=editedCatalog)


@app.route('/<string:catalog_name>/delete/', methods=['GET', 'POST'])
def deleteCatalog(catalog_name):
    catalogToDelete = session.query(Catalog).filter_by(name=catalog_name).one()
    if request.method == 'POST':
        session.delete(catalogToDelete)
        session.commit()
        return redirect(url_for('showCatalogs'))
    else:
        return render_template('catalogDelete.html', catalog=catalogToDelete)


"""
Category Section
"""
@app.route('/<string:catalog_name>/categories')
def showCategories(catalog_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    categories = session.query(Category).filter_by(catalog_id = catalog.catalog_id).all()
    return render_template('categoryList.html', categories=categories, catalog=catalog)


@app.route('/<string:catalog_name>/categories/new/', methods=['GET', 'POST'])
def newCategory(catalog_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    if request.method == 'POST':
        newCategory = Category(name=request.form['name'], description=request.form['description'], catalog_id = catalog.catalog_id)
        session.add(newCategory)
        session.commit()
        return redirect(url_for('showCategories', catalog_name = catalog.name))
    else:
        return render_template('categoryNew.html', catalog=catalog)

# editCategory
@app.route('/<string:catalog_name>/<string:category_name>/edit/', methods=['GET', 'POST'])
def editCategory(catalog_name, category_name):
    parentCatalog = session.query(Catalog).filter_by(name=catalog_name).one()
    editedCategory = session.query(Category).filter_by(catalog_id=parentCatalog.catalog_id, name=category_name).one()
    if request.method == 'POST':
        editedCategory.name = request.form['name']
        editedCategory.description = request.form['description']
        return redirect(url_for('showCategories', catalog_name = parentCatalog.name))
    else:
        return render_template('categoryEdit.html', catalog=parentCatalog, category=editedCategory)


# showCategory
@app.route('/<string:catalog_name>/<string:category_name>/')
def showCategory(catalog_name, category_name):
    showCatalog = session.query(Catalog).filter_by(name=catalog_name).one()
    showCategory = session.query(Category).filter_by(catalog_id = showCatalog.catalog_id, name=category_name).one()
    showItems = session.query(Item).filter_by(category_id = showCategory.category_id).all()
    return render_template('categoryItemList.html', category=showCategory, catalog=showCatalog, items=showItems)


# showCategoryItems
@app.route('/<string:catalog_name>/<string:category_name>/items/')
def showCategoryItems(catalog_name, category_name):
    showCatalog = session.query(Catalog).filter_by(name=catalog_name).one()
    showCategory = session.query(Category).filter_by(catalog_id = showCatalog.catalog_id, name=category_name).one()
    showItems = session.query(Item).filter_by(category_id = showCategory.category_id).all()
    return render_template('categoryItemList.html', catalog=showCatalog, category=showCategory, items=showItems)


# deleteCategory
@app.route('/<string:catalog_name>/<string:category_name>/delete/', methods=['GET', 'POST'])
def deleteCategory(catalog_name, category_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    category = session.query(Category).filter_by(catalog_id = catalog.catalog_id, name=category_name).one()
    if request.method == 'POST':
        session.delete(category)
        session.commit()
        return redirect(url_for('showCategories', catalog_name=catalog.name))
    else:
        return render_template('categoryDelete.html', catalog=catalog, category=category)


if __name__ == "__main__":
    app.secret_key = '0fldskt54l35k4'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)