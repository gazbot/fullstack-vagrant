from flask import Flask, render_template, request
from flask import redirect, url_for, jsonify, flash
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
import os
import uuid
from flask import make_response
import requests

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Udacity Item Catalog"
UPLOAD_FOLDER = 'static/upload'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
MAX_CONTENT_LENGTH = 2 * 1024 * 1024

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Limit size of uploaded files
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state, CLIENT_ID=CLIENT_ID)


@app.route('/auth/google/connect', methods=['POST'])
def googleConnect():
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
        response = make_response(
            json.dumps('Current user is already connected.'),
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
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
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
    try:
        user = session.query(User).filter_by(user_id=user_id).one()
        return user
    except:
        return None


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.user_id
    except:
        return None


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/auth/google/disconnect')
def googleDisconnect():
        # Only disconnect a connected user.
    if 'username' not in login_session:
        response = make_response(
            json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = login_session.get('credentials')
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


@app.route('/auth/logout')
def userLogout():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    if 'username' not in login_session:
        return render_template(
            'unauthorised.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        return render_template(
            'loggedOut.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)


@app.route('/user/profile')
def userProfile():
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'unauthorised.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template('userProfile.html', user=user)


@app.route('/items/<item_name>/')
def showItem(item_name):
    item = session.query(Item).filter_by(name=item_name).one()
    if request.headers['Content-Type'] == 'application/json':
        return jsonify(item=item.serialize)

    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'publicItemDisplay.html',
            item=item,
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template('itemDisplay.html', item=item, user=user)


# Edit the named item
@app.route('/items/<item_name>/edit/', methods=['GET', 'POST'])
def editItem(item_name):
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'unauthorised.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        categories = session.query(Category).all()
        item = session.query(Item).filter_by(name=item_name).one()
        itemCategory = session.query(Category).filter_by(
            category_id=item.category_id).one()
        owner = item.creation_user
        if request.method == 'POST':
            if owner.user_id != user.user_id:
                return redirect(
                    url_for('unauthorised.html'),
                    STATE=state,
                    CLIENT_ID=CLIENT_ID)
            else:
                editItemCategory = session.query(Category).filter_by(
                    name=request.form['category']).one()
                item.name = request.form['name']
                item.description = request.form['description']
                item.category_id = editItemCategory.category_id
                return redirect(url_for('showItem', item_name=item.name))
        else:
            return render_template(
                'itemEdit.html',
                categories=categories,
                item=item,
                itemCategory=itemCategory,
                user=user,
                owner=owner)


# Deletes the named item, displays confirmation page before removal
@app.route('/items/<item_name>/delete/', methods=['GET', 'POST'])
def deleteItem(item_name):
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'unauthorised.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        itemToDelete = session.query(Item).filter_by(name=item_name).one()
        if login_session['user_id'] != itemToDelete.creation_user.user_id:
            responseScript = "<script>function myFunction() {alert('"
            responseScript += "You are not authorized to delete this item."
            responseScript += "');}</script><body onload='myFunction()''>"
            return responseScript
        if request.method == 'POST':
            session.delete(itemToDelete)
            session.commit()
            return redirect(url_for('listItems'))
        else:
            return render_template(
                'itemDelete.html',
                user=user,
                item=itemToDelete)


# Creates a new item
@app.route('/items/new/', methods=['GET', 'POST'])
def newItem():
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'unauthorised.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        if request.method == 'POST':
            file = request.files['file']
            if file is None:
                picture_path = '/static/images/blank.png'
            else:
                extension = os.path.splitext(file.filename)[1]
                f_name = str(uuid.uuid4()) + extension
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], f_name))
                picture_path = '/static/upload/' + f_name
            category = session.query(Category).filter_by(
                name=request.form['category']).one()
            item = Item(
                name=request.form['name'],
                description=request.form['description'],
                category_id=category.category_id,
                creation_user=user,
                picture_url=picture_path)
            session.add(item)
            session.commit()
            return redirect(url_for('listItems'))
        else:
            categories = session.query(Category).all()
            return render_template(
                'itemNew.html',
                categories=categories,
                user=user)


# List items, supports certain query parameters,
# list orderBy / page / pageSize
@app.route('/items/')
def listItems():
    items = session.query(Item).all()
    if request.headers['Content-Type'] == 'application/json':
        return jsonify(items=[i.serialize for i in items])
    if request.headers['Content-Type'] == 'text/xml':
        itemXmlTemplate = "\t<item>\n\t\t<name>%(name)s</name>\n\t\t"
        itemXmlTemplate += "<description>%(description)s</description>\n\t\t"
        itemXmlTemplate += "<picture_url>%(picture_url)s</picture_url>\n\t\t"
        itemXmlTemplate += "<creation_user_id>%(creation_user_id)s</creation_user_id>\n\t\t"
        itemXmlTemplate += "<creation_date>%(creation_date)s</creation_date>"
        itemXmlTemplate += "\n\t</item>"
        responseXml = '<?xml version="1.0" encoding="UTF-8" ?>\n<items>\n'
        for item in items:
            data = {'item_id': item.item_id,
                    'name': item.name,
                    'description': item.description,
                    'picture_url': item.picture_url,
                    'category_id': item.category_id,
                    'creation_user_id': item.creation_user_id,
                    'creation_date': item.creation_date}
            responseXml += itemXmlTemplate % data
        responseXml += "</items>"
        response = make_response(responseXml, 200)
        response.headers['Content-Type'] = 'text/xml'
        return response
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'publicItemList.html',
            items=items,
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template('itemList.html', items=items, user=user)


"""
Category Section
"""


@app.route('/')
@app.route('/categories')
def showCategories():
    categories = session.query(Category).all()
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'publicCategoryList.html',
            categories=categories,
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template(
            'categoryList.html',
            categories=categories,
            user=user)


@app.route('/categories/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'unauthorised.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        if request.method == 'POST':
            newCategory = Category(
                name=request.form['name'],
                description=request.form['description'])
            session.add(newCategory)
            session.commit()
            return redirect(url_for('showCategories'))
        else:
            return render_template('categoryNew.html', user=user)


# editCategory
@app.route('/category/<string:category_name>/edit/', methods=['GET', 'POST'])
def editCategory(category_name):
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'unauthorised.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        editedCategory = session.query(
            Category).filter_by(name=category_name).one()
        owner = editedCategory.creation_user
        if request.method == 'POST':
            if owner.user_id != user.user_id:
                return redirect(
                    url_for('unauthorised.html'),
                    STATE=state,
                    CLIENT_ID=CLIENT_ID)
            else:
                editedCategory.name = request.form['name']
                editedCategory.description = request.form['description']
                return redirect(url_for('showCategories'))
        else:
            return render_template(
                'categoryEdit.html',
                category=editedCategory,
                user=user)


# showCategory
@app.route('/category/<string:category_name>/')
def showCategory(category_name):
    showCategory = session.query(Category).filter_by(name=category_name).one()
    showItems = session.query(Item).filter_by(
        category_id=showCategory.category_id).all()
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'publicCategoryItemList.html',
            category=showCategory,
            items=showItems,
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template(
            'categoryItemList.html',
            category=showCategory,
            items=showItems,
            user=user)


# showCategoryItems
@app.route('/category/<string:category_name>/items/')
def showCategoryItems(category_name):
    showCategory = session.query(Category).filter_by(name=category_name).one()
    showItems = session.query(Item).filter_by(
        category_id=showCategory.category_id).all()
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'publicCategoryItemList.html',
            category=showCategory,
            items=showItems,
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template(
            'categoryItemList.html',
            category=showCategory,
            items=showItems,
            user=user)


# deleteCategory
@app.route('/category/<string:category_name>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_name):
    if 'username' not in login_session:
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template(
            'unauthorised.html',
            STATE=state,
            CLIENT_ID=CLIENT_ID)
    else:
        category = session.query(Category).filter_by(name=category_name).one()
        owner = category.creation_user
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        if request.method == 'POST':
            if owner.user_id != user.user_id:
                return redirect(
                    url_for('unauthorised.html'),
                    STATE=state,
                    CLIENT_ID=CLIENT_ID)
            else:
                session.delete(category)
                session.commit()
                return redirect(url_for('showCategories'))
        else:
            return render_template(
                'categoryDelete.html',
                category=category,
                user=user)


if __name__ == "__main__":
    app.secret_key = '0fldskt54l35k4'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
