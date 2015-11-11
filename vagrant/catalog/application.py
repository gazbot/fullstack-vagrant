from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import random
import string
from flask import make_response
import requests

# OAuth imports
# from flask import session as login_session
# import random, string

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

APPLICATION_NAME = "Udacity Item Catalog"

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


"""
Endpoints
  ** category **
/
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

# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state, CLIENT_ID=CLIENT_ID)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(username=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.user_id


def getUserInfo(user_id):
    user = session.query(User).filter_by(user_id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.user_id
    except:
        return None


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response
        

"""
Items Section
"""
@app.route('/items/<item_name>/')
def showItem(item_name):
    item = session.query(Item).filter_by(name=item_name).one()
    return render_template('itemDisplay.html', item=item)
    
 
# Edit the named item
@app.route('/items/<item_name>/edit/', methods=['GET', 'POST'])
def editItem(item_name):
    categories = session.query(Category).all()
    item = session.query(Item).filter_by(name=item_name).one()
    itemCategory = session.query(Category).filter_by(category_id=item.category_id).one()
    if request.method == 'POST':
        editItemCategory = session.query(Category).filter_by(name=request.form['category']).one()
        item.name = request.form['name']
        item.description = request.form['description']
        item.category_id = editItemCategory.category_id
        return redirect(url_for('showItem', item_name=item.name))
    else:
        return render_template('itemEdit.html', categories=categories, item=item, itemCategory=itemCategory)  
  
  
# Deletes the named item, displays confirmation page before removal 
@app.route('/items/<item_name>/delete/', methods=['GET', 'POST'])
def deleteItem(item_name):
    itemToDelete = session.query(Item).filter_by(name=item_name).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('listItems'))
    else:
        return render_template('itemDelete.html', item=itemToDelete)


# Creates a new item
@app.route('/items/new/', methods=['GET', 'POST'])
def newItem():
    if request.method == 'POST':
        category = session.query(Category).filter_by(name=request.form['category']).one()
        item = Item(name=request.form['name'], description=request.form['description'], category_id=category.category_id)
        session.add(item)
        session.commit()
        return redirect(url_for('listItems'))
    else:
        categories = session.query(Category).all()
        return render_template('itemNew.html', categories=categories)
    

# List items, supports certain query parameters,
# list orderBy / page / pageSize 
@app.route('/items/')
def listItems():
    items = session.query(Item).all()
    return render_template('itemList.html', items=items)

 
"""
Category Section
"""
@app.route('/')
@app.route('/categories')
def showCategories():
    categories = session.query(Category).all()
    return render_template('categoryList.html', categories=categories)


@app.route('/categories/new/', methods=['GET', 'POST'])
def newCategory():
    if request.method == 'POST':
        newCategory = Category(name=request.form['name'], description=request.form['description'])
        session.add(newCategory)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('categoryNew.html')

# editCategory
@app.route('/category/<string:category_name>/edit/', methods=['GET', 'POST'])
def editCategory(category_name):
    editedCategory = session.query(Category).filter_by(name=category_name).one()
    if request.method == 'POST':
        editedCategory.name = request.form['name']
        editedCategory.description = request.form['description']
        return redirect(url_for('showCategories'))
    else:
        return render_template('categoryEdit.html', category=editedCategory)


# showCategory
@app.route('/category/<string:category_name>/')
def showCategory(category_name):
    showCategory = session.query(Category).filter_by(name=category_name).one()
    showItems = session.query(Item).filter_by(category_id = showCategory.category_id).all()
    return render_template('categoryItemList.html', category=showCategory, items=showItems)


# showCategoryItems
@app.route('/category/<string:category_name>/items/')
def showCategoryItems(category_name):
    showCategory = session.query(Category).filter_by(name=category_name).one()
    showItems = session.query(Item).filter_by(category_id = showCategory.category_id).all()
    return render_template('categoryItemList.html', category=showCategory, items=showItems)


# deleteCategory
@app.route('/category/<string:category_name>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    if request.method == 'POST':
        session.delete(category)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('categoryDelete.html', category=category)


if __name__ == "__main__":
    app.secret_key = '0fldskt54l35k4'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)