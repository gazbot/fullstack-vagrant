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
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# Login endpoint
@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state, CLIENT_ID=CLIENT_ID)


# Google OAuth Connect endpoint
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

    # display the successful login to the user
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


# Create User endpoint
def createUser(login_session):
    newUser = User(username=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.user_id


# Get User Information (by user_id) endpoint
def getUserInfo(user_id):
    try:
        user = session.query(User).filter_by(user_id=user_id).one()
        return user
    except:
        return None


# Get User ID (by email) endpoint
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.user_id
    except:
        return None


# If the provided filename has a valid extension return true.
def allowedFile(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# Google OAuth 2.0 Disconnect Account endpoint
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


# Logout endpoint
@app.route('/auth/logout')
def userLogout():
    # generate a new random session state token
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    # set the state token to the newly generated state token
    login_session['state'] = state
    if 'username' not in login_session:
        # no username as been set, access is restricted for this function
        return render_template('unauthorised.html', STATE=state,
                               CLIENT_ID=CLIENT_ID)
    else:
        # remove the user details from the current session.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        return render_template('loggedOut.html', STATE=state,
                               CLIENT_ID=CLIENT_ID)


# Current User Information endpoint
@app.route('/user/profile')
def userProfile():
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, access is restricted for this function
        return render_template('unauthorised.html', STATE=state,
                               CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template('userProfile.html', user=user)


# Item Detail endpoint
@app.route('/items/<item_name>/')
def showItem(item_name):
    item = session.query(Item).filter_by(name=item_name).one()
    # the request specifies JSON as the desired response
    if request.headers['Content-Type'] == 'application/json':
        # JSONify the data
        jsonResponse = jsonify(item=item.serialize)
        # add the JSON data to the response with status OK
        response = make_response(jsonResponse, 200)
        # set the response header to JSON
        response.headers['Content-Type'] = 'application/json'
        return response

    # the request specifies XML as the desired response
    if request.headers['Content-Type'] == 'text/xml':
        # standard XML header
        xml = '<?xml version="1.0" encoding="UTF-8" ?>\n'
        # define the XML template for a single item
        xmlItem = "<item>\n\t<name>%(name)s</name>\n\t"
        xmlItem += "<description>%(description)s</description>\n\t"
        xmlItem += "<picture_url>%(picture_url)s</picture_url>\n\t"
        xmlItem += "<category_id>%(category_id)s</category_id>\n\t"
        xmlItem += "<creation_user_id>%(creation_user_id)s</creation_user_id>"
        xmlItem += "\n\t\t<creation_date>%(creation_date)s</creation_date>\n"
        xmlItem += "</item>"
        # bind the data from the item class to use in the template
        itemData = {'item_id': item.item_id,
                    'name': item.name,
                    'description': item.description,
                    'picture_url': item.picture_url,
                    'category_id': item.category_id,
                    'creation_user_id': item.creation_user_id,
                    'creation_date': item.creation_date}
        # combine the template xml with the item data and add to
        # the XML
        xml += xmlItem % itemData
        # add the XML to the response and set to be OK
        response = make_response(xml, 200)
        # set the content type of the response to be XML
        response.headers['Content-Type'] = 'text/xml'
        return response
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, display the public version
        return render_template('publicItemDisplay.html', item=item,
                               STATE=state, CLIENT_ID=CLIENT_ID)
    else:
        # username has been set, set the required values for the navbar
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        # display the user only version of the page
        return render_template('itemDisplay.html', item=item, user=user)


# Edit Item endpoint
@app.route('/items/<item_name>/edit/', methods=['GET', 'POST'])
def editItem(item_name):
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, access restricted
        return render_template('unauthorised.html', STATE=state,
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
                return redirect(url_for('unauthorised.html'), STATE=state,
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


# Delete Item endpoint
@app.route('/items/<item_name>/delete/', methods=['GET', 'POST'])
def deleteItem(item_name):
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, access restricted
        return render_template('unauthorised.html', STATE=state,
                               CLIENT_ID=CLIENT_ID)
    else:
        # obtain user details
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        # obtain item information
        itemToDelete = session.query(Item).filter_by(name=item_name).one()
        # confirm the user is allowed to delete this item
        if login_session['user_id'] != itemToDelete.creation_user.user_id:
            # current user is not the use who created this item, prevent
            # deletion and alert the current user.
            responseScript = "<script>function myFunction() {alert('"
            responseScript += "You are not authorized to delete this item."
            responseScript += "');}</script><body onload='myFunction()''>"
            return responseScript

        if request.method == 'POST':
            # current user created the item, proceed to delete.
            session.delete(itemToDelete)
            session.commit()
            return redirect(url_for('listItems'))
        else:
            # display the confirmation of deletion template to user.
            return render_template('itemDelete.html', user=user,
                                   item=itemToDelete)


# New Item endpoint
@app.route('/items/new/', methods=['GET', 'POST'])
def newItem():
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, access is restricted for this function
        return render_template('unauthorised.html', STATE=state,
                               CLIENT_ID=CLIENT_ID)
    else:
        # collect user details from login session
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        if request.method == 'POST':
            # collect the file information from request
            file = request.files['file']
            if file is None and not allowedFile(file.filename):
                # no image provided or invalid extension
                # use the default blank image
                picture_path = '/static/images/blank.png'
            else:
                # grab the extension of the file
                extension = os.path.splitext(file.filename)[1]
                # create a unique filename (UUID/GUID)
                f_name = str(uuid.uuid4()) + extension
                # save the new filename with the original extension
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], f_name))
                # path of the picture to use for the template
                picture_path = app.config['UPLOAD_FOLDER'] + f_name

            # find the matching category from the picklist
            category = session.query(Category).filter_by(
                name=request.form['category']).one()
            # create the new item with appropriate values
            item = Item(name=request.form['name'],
                        description=request.form['description'],
                        category_id=category.category_id,
                        creation_user=user,
                        picture_url=picture_path)
            # save the newly created item.
            session.add(item)
            session.commit()
            # item added, go back and display the list of items
            return redirect(url_for('listItems'))
        else:
            # query the database and get all categories to display in picklist
            categories = session.query(Category).all()
            # display the new item template
            return render_template('itemNew.html',
                                   categories=categories,
                                   user=user)


# Item List endpoint
@app.route('/items/')
def listItems():
    items = session.query(Item).all()
    # the request specifies JSON as the desired response
    if request.headers['Content-Type'] == 'application/json':
        # JSONify the data
        jsonResponse = jsonify(items=[i.serialize for i in items])
        # add the JSON data to the response with status OK
        response = make_response(jsonResponse, 200)
        # set the response header to JSON
        response.headers['Content-Type'] = 'application/json'
        return response

    if request.headers['Content-Type'] == 'text/xml':
        xml = '<?xml version="1.0" encoding="UTF-8" ?>\n<items>\n'
        itemsXml = "\t<item>\n\t\t<name>%(name)s</name>\n\t\t"
        itemsXml += "<description>%(description)s</description>\n\t\t"
        itemsXml += "<picture_url>%(picture_url)s</picture_url>\n\t\t"
        itemsXml += "<creation_user_id>%(creation_user_id)s</creation_user_id>"
        itemsXml += "\n\t\t<creation_date>%(creation_date)s</creation_date>"
        itemsXml += "\n\t</item>"
        for item in items:
            itemData = {'item_id': item.item_id,
                        'name': item.name,
                        'description': item.description,
                        'picture_url': item.picture_url,
                        'category_id': item.category_id,
                        'creation_user_id': item.creation_user_id,
                        'creation_date': item.creation_date}
            xml += itemsXml % itemData
        xml += "</items>"
        response = make_response(xml, 200)
        response.headers['Content-Type'] = 'text/xml'
        return response
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, display public access to page
        return render_template('publicItemList.html', items=items,
                               STATE=state, CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template('itemList.html', items=items, user=user)


# Default route, category listing
@app.route('/')
@app.route('/categories')
def showCategories():
    categories = session.query(Category).all()
    # the request specifies JSON as the desired response
    if request.headers['Content-Type'] == 'application/json':
        # JSONify the data
        jsonResponse = jsonify(categories=[c.serialize for c in categories])
        # add the JSON data to the response with status OK
        response = make_response(jsonResponse, 200)
        # set the response header to JSON
        response.headers['Content-Type'] = 'application/json'
        return response

    if request.headers['Content-Type'] == 'text/xml':
        xml = '<?xml version="1.0" encoding="UTF-8" ?>\n'
        xml += '<categories>\n'
        catXml = '\t<category>\n'
        catXml += '\t\t<category_id>%(category_id)s</category_id>\n'
        catXml += '\t\t<name>%(name)s</name>\n'
        catXml += '\t\t<description>%(description)s</description>\n'
        catXml += '\t\t<creation_user_id>%(user_id)s</creation_user_id>\n'
        catXml += '\t\t<creation_date>%(creation_date)s</creation_date>\n'
        catXml += '\t</category>\n'
        for category in categories:
            catData = {'category_id': category.category_id,
                       'name': category.name,
                       'description': category.description,
                       'user_id': category.creation_user_id,
                       'creation_date': category.creation_date}
            xml += catXml % catData
        xml += '</categories>\n'
        response = make_response(xml, 200)
        response.headers['Content-Type'] = 'text/xml'
        return response

    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, display public access to page
        return render_template('publicCategoryList.html',
                               categories=categories, STATE=state,
                               CLIENT_ID=CLIENT_ID)
    else:
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        return render_template('categoryList.html',
                               categories=categories,
                               user=user)


# New Category endpoint
@app.route('/categories/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, access is restricted
        return render_template('unauthorised.html', STATE=state,
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


# Edit Category endpoint
@app.route('/category/<string:category_name>/edit/', methods=['GET', 'POST'])
def editCategory(category_name):
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, access is restricted.
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
    # the request specifies JSON as the desired response
    if request.headers['Content-Type'] == 'application/json':
        # JSONify the data
        jsonResponse = jsonify(category=showCategory.serialize,
                               items=[i.serialize for i in showItems])
        # add the JSON data to the response with status OK
        response = make_response(jsonResponse, 200)
        # set the response header to JSON
        response.headers['Content-Type'] = 'application/json'
        return response

    # XML
    if request.headers['Content-Type'] == 'text/xml':
        #
        xml = '<?xml version="1.0" encoding="UTF-8" ?>\n'
        catXml = '<category>\n'
        catXml += '\t<category_id>%(category_id)s</category_id>\n'
        catXml += '\t<name>%(name)s</name>\n'
        catXml += '\t<description>%(description)s</description>\n'
        catXml += '\t<creation_user_id>%(user_id)s</creation_user_id>\n'
        catXml += '\t<creation_date>%(creation_date)s</creation_date>\n'
        catXml += '\t<items>\n'

        itemXml = "\t<item>\n\t\t<name>%(name)s</name>\n\t\t"
        itemXml += "<description>%(description)s</description>\n\t\t"
        itemXml += "<picture_url>%(picture_url)s</picture_url>\n\t\t"
        itemXml += "<creation_user_id>%(creation_user_id)s</creation_user_id>"
        itemXml += "\n\t\t<creation_date>%(creation_date)s</creation_date>"
        itemXml += "\n\t</item>"
        # bind the category data for use in template
        catData = {'category_id': showCategory.category_id,
                   'name': showCategory.name,
                   'description': showCategory.description,
                   'user_id': showCategory.creation_user_id,
                   'creation_date': showCategory.creation_date}
        # merge the category data with the xml template into xml response
        xml += catXml % catData

        # iterate through each item and add it to the xml response
        for item in showItems:
            itemData = {'item_id': item.item_id,
                        'name': item.name,
                        'description': item.description,
                        'picture_url': item.picture_url,
                        'category_id': item.category_id,
                        'creation_user_id': item.creation_user_id,
                        'creation_date': item.creation_date}
            # merge the item data with the template and add to xml
            xml += itemXml % itemData

        # close off the item and category tags
        xml += '\t</items>\n'
        xml += '</category>\n'

        # prepare the response for text/xml and add the xml
        response = make_response(xml, 200)
        response.headers['Content-Type'] = 'text/xml'
        return response

    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, display public access to page
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
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, display public access to page
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


# Delete Category endpoint
@app.route('/category/<string:category_name>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_name):
    if 'username' not in login_session:
        # no username, generate a new random session state token
        state = ''.join(random.choice
                        (string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        # set the state token to the newly generated state token
        login_session['state'] = state
        # no username as been set, access is restricted
        return render_template('unauthorised.html', STATE=state,
                               CLIENT_ID=CLIENT_ID)
    else:
        category = session.query(Category).filter_by(name=category_name).one()
        owner = category.creation_user
        email = login_session['email']
        user_id = getUserID(email)
        user = getUserInfo(user_id)
        if request.method == 'POST':
            if owner.user_id != user.user_id:
                return redirect(url_for('unauthorised.html'), STATE=state,
                                CLIENT_ID=CLIENT_ID)
            else:
                session.delete(category)
                session.commit()
                return redirect(url_for('showCategories'))
        else:
            return render_template('categoryDelete.html', category=category,
                                   user=user)


if __name__ == "__main__":
    app.secret_key = '0fldskt54l35k4'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
