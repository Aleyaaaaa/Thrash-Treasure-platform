from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database paths (no changes needed)
database_folder = 'database'
admin_file = os.path.join(database_folder, 'admin.json')
buyer_file = os.path.join(database_folder, 'buyer.json')
seller_file = os.path.join(database_folder, 'sellers.json')
runner_file = os.path.join(database_folder, 'runner.json')
items_file = os.path.join(database_folder, 'items.json')
orders_file = os.path.join(database_folder, 'orders.json')
reviews_file = os.path.join(database_folder, 'reviews.json')
approval_file = os.path.join(database_folder, 'approval.json')
cart_file = os.path.join(database_folder, 'cart.json')
payment_file = os.path.join(database_folder, 'payment.json')
delivery_file = os.path.join(database_folder, 'delivery.json')


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Utility Functions (moved here for clarity)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_form(item_name, item_price, item_description):
    errors = []
    if not 5 <= len(item_name) <= 30:
        errors.append("Item name must be between 5 and 30 characters")

    try:
        float(item_price)
    except ValueError:
        errors.append("Price must be a number.")

    if not 15 <= len(item_description) <= 50:
        errors.append("Item description must be between 15 and 50 characters.")

    return errors

def load_json(filename):
    with open(filename, 'r') as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []

def save_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def load_users(role):
    file_map = {
        'admin': admin_file,
        'buyer': buyer_file,
        'seller': seller_file,
        'runner': runner_file
    }
    return load_json(file_map.get(role, ""))

def read_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def load_items():
    return load_json(items_file)

def save_items(items):
    save_json(items_file, items)

def load_sellers():
    return load_json(seller_file)

def save_sellers(sellers_data):
    save_json(seller_file, sellers_data)

def write_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Modify get_seller_data to find by seller_id
def get_seller_data(seller_id):
    sellers = load_json(seller_file)
    for seller in sellers:
        if seller["id"] == seller_id:
            return seller
    return None

def load_orders():
    return load_json(orders_file)

def save_orders(orders):
    save_json(orders_file, orders)

def load_deliveries():
    return load_json(delivery_file)

def save_deliveries(deliveries):
    save_json(delivery_file, deliveries)


# --- Replace get_next_item_id with a UUID generator ---
def generate_item_id():
    return str(uuid.uuid4())

def get_next_item_id():
    # Load the last used ID from a file (or initialize to 0 if the file doesn't exist)
    id_file = os.path.join(database_folder, 'next_item_id.txt')  # Create a file to track the next ID
    try:
        with open(id_file, 'r') as f:
            content = f.read()
            if content: #If the file is not empty
                next_id = int(content)
            else: # If file is empty
                next_id = 1
    except FileNotFoundError:
        next_id = 1

    # Increment the ID and save it back to the file
    with open(id_file, 'w') as f:
        f.write(str(next_id + 1))

    return next_id

def generate_unique_id(users):
    if not users:
        return 1  # Start from 1 if the user list is empty
    else:
        # Find the maximum existing ID and increment it
        max_id = max(int(user.get('id', 0)) for user in users)
        return max_id + 1

####################################################################### SIGN IN & SIGN UP ##############################################################

@app.route('/')
def home():
    return redirect(url_for('signin'))

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        for role in ['admin', 'buyer', 'seller', 'runner']:
            users = load_users(role)
            for user in users:
                if user['username'] == username and user['password'] == password:
                    session['username'] = username
                    session['role'] = role
                    # Store the user's ID in the session
                    session['id'] = user['id']  #  This assigns the 'id'

                    # Store seller_id in session
                    if role == 'seller':
                        seller_id = user["id"]
                        session["seller_id"] = seller_id
                    return redirect(url_for(f'{role}_dashboard'))

        flash('Invalid username or password', 'danger')
        return redirect(url_for('signin'))

    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        buyers = load_users('buyer')
        new_user_id = generate_unique_id(buyers) # Generate unique ID

        new_user = {
            "id": new_user_id, #Include Unique Id
            "username": username,
            "email": email,
            "password": password,
            "role": "buyer"
        }

        buyers.append(new_user)

        with open(buyer_file, 'w') as file:
            json.dump(buyers, file, indent=4)

        flash('Sign up successful, please sign in!', 'success')
        return redirect(url_for('signin'))

    return render_template('signup.html')


####################################################################### DASHBOARDS ##############################################################

@app.route("/admin_dashboard")
def admin_dashboard():
    if "username" not in session or session.get("role") != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    admin_username = session["username"]

    admins = load_users("admin")
    profile_pic = "static/images/default_admin.jpg"
    for admin in admins:
        if admin["username"] == admin_username:
            profile_pic = admin.get("profile_pic", profile_pic)

    sellers = load_json(seller_file)
    approval = load_json(approval_file)
    orders = load_json(orders_file)
    reviews = load_json(reviews_file)

    total_sellers = len(sellers)
    total_approval = len(approval)
    total_orders = len(orders)
    total_reviews = len(reviews)

    return render_template(
        "admin/admin_dashboard.html",
        username=admin_username,
        profile_pic=profile_pic,
        total_sellers=total_sellers,
        total_approval=total_approval,
        total_orders=total_orders,
        total_reviews=total_reviews
    )

@app.route('/buyer_dashboard')
def buyer_dashboard():
    items = load_items()
    search_query = request.args.get('search', '')

    if search_query:
        items = [item for item in items if search_query.lower() in item['name'].lower()]

    return render_template('buyer/buyer_dashboard.html', items=items)


@app.route('/seller_dashboard')
def seller_dashboard():
    if "username" not in session or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    seller_id = session["seller_id"]

    seller_data = get_seller_data(seller_id)

    if not seller_data:
        flash("Seller not found", "danger")
        return redirect(url_for("signin"))

    profile_pic = seller_data.get("profile_pic", "static/images/default_profile.jpg")
    total_items = len(load_json(items_file))
    total_orders = len(load_json(orders_file))
    total_reviews = len(load_json(reviews_file))

    welcome_message = f"Welcome to Trash & Treasure, {seller_data['username']}!"
    username = seller_data.get("username")

    return render_template(
        'seller/seller_dashboard.html',
        username=username,
        profile_pic=profile_pic,
        total_items=total_items,
        total_orders=total_orders,
        total_reviews=total_reviews,
        welcome_message=welcome_message,
        seller_id=seller_id
    )

@app.route('/runner_dashboard')
def runner_dashboard():
    if "username" not in session or session.get("role") != "runner":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    runner_username = session["username"]  # <--- Get username from session
    runners = load_json(runner_file)

    runner = next((r for r in runners if r["username"] == runner_username), None)  # <--- Match by username

    if not runner:
        flash("Runner not found", "danger")
        return redirect(url_for("signin"))

    profile_pic = runner.get("profile_pic", "static/images/default_runner.jpg")

    orders = [order for order in load_orders() if order.get('status') == 'delivery']

    deliveries = load_deliveries()
    my_list =  [order for order in deliveries if order.get('runner_id') == runner["id"]] # changed from session to username
    total_orders = len(load_orders())

    return render_template(
        'runner/runner_dashboard.html',
        runner=runner,
        profile_pic = profile_pic,
        orders=orders,
        total_orders=total_orders,
        my_list = len(my_list)
    )

####################################################################### SIGN OUT ##############################################################

@app.route('/sign_out', methods=['POST'])
def sign_out():
    role = session.get('role')
    session.clear()
    flash('You have signed out successfully.', 'success')
    return redirect(url_for('signin'))


####################################################################### DELETE PROFILE ##############################################################

@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    if request.form.get('confirm_delete') == 'yes':
        username = session['username']
        role = session['role']

        users = load_users(role)
        users = [user for user in users if user['username'] != username]
        if role == 'seller':
            if save_json(seller_file, users):  # Use sellers_file constant
                # Delete related items, orders, and reviews
                items = load_json(items_file)
                items = [item for item in items if item['seller_id'] != session["seller_id"]]
                save_json(items_file, items)

                orders = load_json(orders_file)
                orders = [order for order in orders if order['seller_id'] != session["seller_id"]]
                save_json(orders_file, orders)

                reviews = load_json(reviews_file)
                reviews = [review for review in reviews if review['seller_id'] != session["seller_id"]]
                save_json(reviews_file, reviews)

                session.clear()
                flash(f'Your profile and all related data have been deleted.', 'danger')
                return redirect(url_for('signin'))
            else:
                flash('Error deleting profile data.', 'danger')
                return redirect(url_for('seller_dashboard'))
        else: #For other user role
            filename = os.path.join(database_folder, f'{role}.json')
            if save_json(filename, users):
                session.clear()
                flash(f'Your profile has been deleted.', 'danger')
                return redirect(url_for('signin'))
            else:
                 flash('Error deleting profile data.', 'danger')
                 return redirect(url_for('seller_dashboard'))

    else:
        flash('Profile deletion aborted.', 'info')
        return redirect(url_for('seller_dashboard'))

####################################################################### ADMIN ##############################################################

@app.route('/seller_profile', methods=['GET'])
def seller_profile():
    sellers = load_sellers()
    seller_id = request.args.get('seller_id', type=int)
    contact_info = None

    if seller_id:
        seller = next((s for s in sellers if s['id'] == seller_id), None)
        if seller:
            contact_info = {'phone': seller['phone'], 'email': seller['email']}

    return render_template('admin/seller_profile.html', sellers=sellers, contact_info=contact_info)

@app.route('/delete_seller/<int:seller_id>', methods=['POST'])
def delete_seller(seller_id):
    sellers = load_sellers()
    seller_to_delete = next((s for s in sellers if s['id'] == seller_id), None)
    if seller_to_delete:
        sellers.remove(seller_to_delete)
        save_sellers(sellers)
        return redirect(url_for('seller_profile', message=f'Seller {seller_to_delete["username"]} deleted.'))
    else:
        return redirect(url_for('seller_profile', message='Seller not found'))


@app.route('/approval')
def approval():
    """Displays the items awaiting approval."""
    approval_items = load_json(approval_file)
    print(f"Approval items loaded: {approval_items}") #debugging purpose
    return render_template('admin/approval.html', items=approval_items, total_items=len(approval_items))

@app.route('/approve/<item_id>', methods=['POST'])  # Remove type constraint
def approve_item(item_id):
    """Approves an item and moves it to the items list with 'approved' status."""

    print(f"approve_item called with item_id: {item_id}")  # Debug
    approval_items = load_json(approval_file)
    print(f"Approval items before: {approval_items}")  # Debug
    items = load_json(items_file)
    print(f"Items before: {items}")  # Debug

    item_found = False
    for item in approval_items[:]:  # Iterate over a copy to allow modification
        # Convert both to strings for comparison
        print(f"Checking item ID: {str(item['id'])}")  # Debug - Print the ID as a string
        if str(item["id"]) == str(item_id):  # Force string comparison
            print("Item found! Approving...")  # Debug
            item["status"] = "approved"
            items.append(item)
            approval_items.remove(item)
            item_found = True
            break

    print(f"Approval items after: {approval_items}")  # Debug
    save_json(approval_file, approval_items)
    print(f"Items after: {items}")  # Debug
    save_json(items_file, items)

    if item_found:
        flash(f"Item with ID {item_id} approved successfully!", "success")
    else:
        flash(f"Item with ID {item_id} not found for approval.", "error")

    return redirect(url_for('approval'))

@app.route('/reject/<string:item_id>', methods=['POST'])
def reject_item(item_id):
    """Rejects an item by removing it from the approval list after confirmation."""
    try:
        approval_items = load_json(approval_file)
        if approval_items is None:
            print("Error: Unable to load approval_items from JSON file - file may be empty or invalid")
            flash("Error loading approval items.", "error")
            return redirect(url_for('approval'))

        # Convert item_id to string to match IDs in JSON data
        item_id = str(item_id)

        # Use list comprehension with string comparison for item IDs
        updated_approval_items = [item for item in approval_items if str(item['id']) != item_id]

        print(f"After filtering, approval_items: {updated_approval_items}")

        if save_json(approval_file, updated_approval_items):
            flash(f"Item with ID {item_id} rejected and removed.", "success")
        else:
            flash("Error saving updated approval list.", "error")

    except FileNotFoundError:
        flash("Approval file not found.", "error")
    except json.JSONDecodeError:
        flash("Invalid JSON in approval file.", "error")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "error")
        print(f"Exception: {e}")
        
    return redirect(url_for('approval'))

@app.route("/orders")
def orders():
    # Load order data from JSON file
    orders = load_json(orders_file)

    # Calculate stats
    total_orders = len(orders)
    orders_completed = 0

    for order in orders:
        if order.get('status') == 'completed':  # Adjust status to 'completed'
            orders_completed += 1

    # Render the template passing the correct variable
    return render_template('admin/orders.html', orders=orders, total_orders=total_orders, orders_completed=orders_completed)

@app.route('/reviews')
def reviews():
    """Displays all reviews with stats for admin."""
    if "username" not in session or session.get("role") != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    all_reviews = load_json(reviews_file)

    # Calculate stats
    total_reviews = len(all_reviews)
    total_rating = 0
    for review in all_reviews:
        total_rating += review.get('rating', 0)

    if total_reviews > 0:
        average_rating = total_rating / total_reviews
    else:
        average_rating = 0

    return render_template(
        'admin/reviews.html',
        all_reviews=all_reviews,
        total_reviews=total_reviews,
        average_rating=average_rating
    )

####################################################################### SELLER ##############################################################

@app.route('/seller_item')
def seller_item():
    if "username" not in session or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    seller_id = session["seller_id"]

    seller_data = get_seller_data(seller_id)

    if not seller_data:
        flash("Seller not found", "danger")
        return redirect(url_for("signin"))

    username = seller_data.get("username")  # Get username for template

    # Retrieve items from items.json based on seller_id
    items = load_json(items_file)
    seller_items = [item for item in items if item["seller_id"] == seller_id]

    return render_template(
        'seller/seller_item.html',
        username=username,
        seller_items=seller_items,
        total_items = len(seller_items)
    )

@app.route('/seller_edititems/<item_id>', methods=['GET', 'POST'])
def seller_edititems(item_id):
    if "username" not in session or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    seller_id = session["seller_id"]
    seller_data = get_seller_data(seller_id)
    username = seller_data.get("username")

    items = load_json(items_file)
    
    # Find the item to edit along with its index
    item_index = None
    item_to_edit = None
    for i, item in enumerate(items):
        if str(item["id"]) == item_id and item["seller_id"] == seller_id:
            item_to_edit = item
            item_index = i
            break


    if not item_to_edit:
        flash("Item not found or unauthorized.", "danger")
        return redirect(url_for("seller_item"))

    if request.method == 'GET':
        return render_template('seller/seller_edititems.html', item=item_to_edit, username=username)  # Show the edit page

    elif request.method == 'POST':  # Handle form Submission
        # Get data from the edit form
        item_name = request.form.get('name')
        item_price = request.form.get('price')
        item_description = request.form.get('description')

        # Handle image upload (Check for new file upload)
        if 'file' in request.files and request.files['file'].filename != '':
            image_file = request.files['file']
            if image_file and allowed_file(image_file.filename):
                filename = str(uuid.uuid4()) + "_" + image_file.filename
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(image_path)
                item_to_edit['image'] = f"/static/uploads/{filename}"  # save image to local file
            else:
                flash("Invalid image format, or no file selected", "error")
                return render_template('seller/seller_edititems.html', item=item_to_edit, username=username) #re-render
        # Validation
        errors = validate_form(item_name, item_price, item_description)
        if errors:
            flash(' , '.join(errors),"error")
            return render_template('seller/seller_edititems.html', item=item_to_edit, username=username)  # Show the edit page

        # Update the item's details
        item_to_edit['name'] = item_name
        item_to_edit['price'] = f"RM {float(item_price):.2f}"
        item_to_edit['description'] = item_description

        # Load approval items
        approval_items = load_json(approval_file)

        # Add the updated item to approval_items
        approval_items.append(item_to_edit)
        save_json(approval_file, approval_items)
        
        # Remove the item from items.json, if it's found.  The index should never be none since we are finding the Item ID before this
        if item_index is not None:
            del items[item_index]
            save_items(items)

        flash("Item changes submitted for approval!", "success")
        return redirect(url_for('seller_item'))
    
    
@app.route('/seller_removeitems/<item_id>')
def seller_removeitems(item_id):
    print("seller_removeitems function called") # This is for logging.
    if "username" not in session or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    seller_id = session["seller_id"]
    print(f"The seller id is = {seller_id}") # for logging
    items = load_json(items_file)
    print(f"Load items is = {items}") # for logging
    item_to_remove = next(
        (item for item in items
         if str(item["id"]) == str(item_id) and item["seller_id"] == seller_id),
        None
    )

    if not item_to_remove:
        flash("Item not found or unauthorized.", "danger")
        print("Item not found or unauthorized. Redirecting...") # for logging
        return redirect(url_for("seller_item"))
    print(f"Item to remove = {item_to_remove}") # for logging

    # Find the item's index to remove it
    item_index = None
    for i, item in enumerate(items):
        if str(item["id"]) == str(item_id) and item["seller_id"] == seller_id:
            item_index = i
            break

    if item_index is not None:
        print(f"Item index found {item_index}") #for logging
        del items[item_index]
        print(f"After deletion items = {items}") #for logging
        save_items(items)
        flash("Item removed successfully!", "success")
        print("Saving complete and redirecting") #for logging

    else:
        print("Error finding the item")#for logging
        flash("Item not found or unauthorized.", "danger")

    return redirect(url_for('seller_item'))

@app.route('/seller_additems', methods=['GET','POST'])
def seller_additems():
    if "username" not in session or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    seller_id = session["seller_id"]

    seller_data = get_seller_data(seller_id)

    if not seller_data:
        flash("Seller not found", "danger")
        return redirect(url_for("signin"))

    username = seller_data.get("username") # Get username for template

    if request.method == 'POST':

        if 'file' not in request.files:
            flash("No item image uploaded", "error")
            return redirect(url_for("seller_additems"))

        image_file = request.files['file']
        item_name = request.form.get('name')
        item_price = request.form.get('price')
        item_description = request.form.get('description')


        if image_file and allowed_file(image_file.filename):
            errors = validate_form(item_name, item_price,item_description)

            if errors:
                flash(' , '.join(errors),"error")
                return redirect(url_for("seller_additems"))


            filename =  str(uuid.uuid4()) + "_" +image_file.filename
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(image_path)

            # seller_id = seller_data.get("id", "Unknown ID") # seller_id is the function parameter
            item_id = get_next_item_id()


            new_item = {
                'id' : item_id,
                'seller_id': seller_id,
                'image':  f"/static/uploads/{filename}",
                'name':item_name,
                'price': f"RM {float(item_price):.2f}",
                'description': item_description
            }


            approval = load_json(approval_file)
            approval.append(new_item)
            save_json(approval_file,approval)

            flash("Item successfully added to await approval by admin",'success')
            return redirect(url_for("seller_additems"))


        else :
            flash("Invalid image format, or no file selected","error")
            return redirect(url_for("seller_additems"))


    items = load_json(items_file)
    seller_items = [item for item in items if item["seller_id"] == seller_id] # Filter using seller_id

    return render_template(
        'seller/seller_additems.html',  # Changed
        username=username,
        seller_items=seller_items
    )

@app.route('/seller_orders/<username>')
def seller_orders(username):
    if "username" not in session or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    seller_id = session.get('seller_id')  # Get seller_id from session

    # Filter orders based on seller_id ONLY
    seller_orders = [
        order for order in load_orders()
        if order.get("seller_id") == seller_id
    ]

    print("DEBUG: seller_orders =", seller_orders)  # Add this line for debugging

    seller_data = get_seller_data(session.get('seller_id')) # Get the username of the seller for displaying user in seller's dashboard
     # Render the template, using the seller's actual username
    return render_template(
        'seller/seller_orders.html',
        username=seller_data.get("username"),  # Pass the actual username to the template
        seller_orders=seller_orders
    )

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    order_id = int(request.form['order_id'])
    new_status = request.form['new_status']
    seller_id = session.get('seller_id')  # Get seller_id from session

    if not seller_id or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    orders = load_orders()
    # deliveries = load_deliveries() # no more

    for order in orders:
        if order['id'] == order_id and order.get('seller_id') == seller_id:  # Verify seller_id ONLY
            if new_status == 'in progress' and order['status'] != 'in progress':
                order['status'] = 'in progress'
            elif new_status == 'delivery' and order['status'] == 'in progress':
                order['status'] = 'delivery'
                # deliveries.append(order) # no more
                # orders.remove(order) #no more
            break

    save_orders(orders)
    # save_deliveries(deliveries) # no more
    return redirect(url_for('seller_orders', username=session.get('username')))

@app.route('/seller_reviews')
def seller_reviews():
    """Displays reviews for the seller's items and allows the seller to add replies."""
    if "username" not in session or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    seller_id = session["seller_id"]
    seller_data = get_seller_data(seller_id)

    reviews = load_json(reviews_file)
    # Filter item by using their seller ID
    seller_reviews = [review for review in reviews if review['seller_id'] == seller_id]

    # Calculate stats
    total_reviews = len(seller_reviews)
    total_rating = 0 #set default to 0

    for review in seller_reviews: #Loop check
        total_rating += review.get('rating', 0)

    if total_reviews > 0:
        average_rating = total_rating / total_reviews
    else:
        average_rating = 0  # Avoid division by zero

    # Prepare review data for the template, pre-populating the reply if it exists
    for review in seller_reviews:
        review['reply'] = review.get('replies', '')  # Use 'reply' key in template


    username = seller_data.get("username") #Get username for template


    return render_template('seller/seller_reviews.html', seller_reviews=seller_reviews, username=username, total_reviews=total_reviews, average_rating=average_rating)

@app.route('/submit_reply/<int:review_id>', methods=['POST'])
def submit_reply(review_id):
    """Handles the submission of a seller's reply to a review."""
    if "username" not in session or session.get("role") != "seller":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    reply = request.form.get('reply') #Getting current reply
    seller_id = session["seller_id"]  #get id seller
    reviews = load_json(reviews_file) #Load all Reviews

    for review in reviews: #Search for their id and then filter
        if review['id'] == review_id and review['seller_id'] == seller_id:
            review['replies'] = reply  # Set the 'replies' key to the reply text
            save_json(reviews_file, reviews)
            flash("Reply submitted successfully!", "success")
            return redirect(url_for('seller_reviews'))

    flash("Error submitting reply.", "error")
    return redirect(url_for('seller_reviews'))

####################################################################### BUYER ##############################################################

@app.route('/buyer_items')
def buyer_items():
    items = load_items()
    return render_template('buyer/buyer_dashboard.html', items=items)

@app.route('/buyer_cart')
def buyer_cart():
    cart_items = load_json(cart_file)
    print(cart_items) #Add this line to test and view at the backend side to see if the cart items is loaded
    return render_template('buyer/buyer_cart.html', cart_items=cart_items)

@app.route('/item/<int:item_id>')
def item_details(item_id):
    items = load_json(items_file)
    item = next((item for item in items if item['id'] == item_id), None)

    if item is None:
        return "Item not found", 404

    return render_template('buyer/item_details.html', item=item)

@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    items = load_json(items_file)
    cart_items = load_json(cart_file)

    item = next((item for item in items if item['id'] == item_id), None)

    if item is None:
        return "Item not found", 404

    cart_items.append(item)
    save_json(cart_file, cart_items)
    return redirect(url_for('item_details', item_id=item_id))

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart_items = load_json(cart_file)
    item_to_remove = next((item for item in cart_items if item['id'] == item_id), None)

    if item_to_remove:
        cart_items = [item for item in cart_items if item['id'] != item_id]
        save_json(cart_file, cart_items)
        flash(f"{item_to_remove['name']} has been removed from your cart", 'success')
    else:
        flash("Item not found in cart", 'error')

    return redirect(url_for('buyer_cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    cart_items = load_json(cart_file)
    if not cart_items:
        flash("Your cart is empty", "error")
        return redirect(url_for('buyer_cart'))

    delivery_address = request.form.get('delivery_address')
    if not delivery_address:
        flash("Delivery address is required", "error")
        return redirect(url_for('buyer_cart'))

    #Move items to payment.json (and clear cart)
    payment_data = load_json(payment_file)

    # Attach delivery address to each item
    for item in cart_items:
        item['delivery_address'] = delivery_address  # Add delivery address

    payment_data.extend(cart_items) #Append all cart items

    save_json(payment_file, payment_data)

    #Clear the cart
    save_json(cart_file,[])

    flash("Checkout successful! Redirecting to payment.", "success") #Flash a success message
    return redirect(url_for('payment'))  # Redirect to a payment page

@app.route('/payment')
def payment():
    payment_data = load_json(payment_file)
    return render_template('buyer/payment.html',payment_data = payment_data)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    payment_method = request.form.get('payment_method')
    card_number = request.form.get('card_number')  # In a real app, *never* store card numbers!
    expiry_date = request.form.get('expiry_date')
    cvv = request.form.get('cvv')
    buyer_id = session.get('id')  # Assuming you store the buyer ID in the session

    payment_data = load_json(payment_file)
    orders = load_json(orders_file)
    items = load_json(items_file)

    # Move payment data to orders and update item status
    for item in payment_data:
        item['status'] = 'paid'  # Update status for paid
        item['buyer_id'] = buyer_id  # Add buyer_id to each item
        orders.append(item)  # Move the item to the order list

    # Update items in items.json
    for item in payment_data:
        # Remove the specific one from `items_file`
        items = [existing_item for existing_item in items if existing_item['id'] != item['id']]  # Remove item

    save_json(items_file, items)
    save_json(orders_file, orders)

    # Clear the payment file
    save_json(payment_file, [])  # Clear all the items since its all "paid"

    flash("Payment Successful", "success")
    return redirect(url_for('buyer_dashboard'))  # Redirect to the dashboard

@app.route('/buyer_reviews')
def buyer_reviews():
    """Displays completed orders and allows buyers to submit reviews, filtered for the current buyer only."""
    if "username" not in session or session.get("role") != "buyer":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    buyer_id = session.get('id')  # Get buyer's ID from the session

    if not buyer_id:
        flash("Buyer ID not found in session.", "error")
        return redirect(url_for("signin"))

    reviews = load_json(reviews_file)
    orders = load_json(orders_file)

    # Filter orders to only those completed AND matching the buyer_id in session
    completed_orders = [
        order for order in orders
        if order['status'] == 'completed' and order.get('buyer_id') == buyer_id
    ]

    # Prepare review data for the template, pre-populating the data from reviews
    for order in completed_orders:
        review = next((review for review in reviews
                       if review['id'] == order['id'] and review.get('buyer_id') == buyer_id), None)
        
        # Load and prep the data on all scenario
        if review:
            order['review_text'] = review.get('review_text', '')
            order['rating'] = review.get('rating', 0)
            order['replies'] = review.get('replies', '')
        else:
            order['review_text'] = '' #Adding empty value
            order['rating'] = 0
            order['replies'] = ''#Adding empty value

    return render_template('buyer/buyer_reviews.html', completed_orders=completed_orders, reviews=reviews)

@app.route('/submit_review/<int:item_id>', methods=['POST'])
def submit_review(item_id):
    """Handles the submission of a buyer's review and rating."""
    if "username" not in session or session.get("role") != "buyer":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    feedback = request.form.get('feedback')
    rating = request.form.get(f'rating-{item_id}')

    if not rating:
        flash("Please select a rating.", "error")
        return redirect(url_for('buyer_reviews'))

    reviews = load_json(reviews_file)
    #Search For the item in reviews if its match with order and the item
    for review in reviews:
        #If the review match with the item and user proceed to update the review and save
        if review['id'] == item_id:
            review['review_text'] = feedback
            review['rating'] = int(rating)  # Convert to integer

            save_json(reviews_file, reviews)
            flash("Thank you for your feedback!", "success")
            return redirect(url_for('buyer_reviews'))

    flash("Error submitting review.", "error")
    return redirect(url_for('buyer_reviews'))

@app.route('/buyer_status')
def buyer_status():
    """Displays all orders for the logged-in buyer."""
    if "username" not in session or session.get("role") != "buyer":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    buyer_id = session.get('id')

    if not buyer_id:
        flash("Buyer ID not found in session.", "error")
        return redirect(url_for("signin"))

    orders = load_json(orders_file)

    # Filter for items purchased by the current buyer, irrespective of status
    buyer_items = [
        order for order in orders
        if order.get('buyer_id') == buyer_id
    ]

    return render_template('buyer/buyer_status.html', items=buyer_items)
####################################################################### RUNNER ##############################################################

@app.route('/my_list')
def my_list():
    if "username" not in session or session.get("role") != "runner":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    runner_username = session["username"]
    runners = load_json(runner_file)

    runner = next((r for r in runners if r["username"] == runner_username), None)

    if not runner:
        flash("Runner not found", "danger")
        return redirect(url_for("signin"))

    runner_id = runner["id"]

    deliveries = load_deliveries()
    my_deliveries = [delivery for delivery in deliveries if delivery.get('runner_id') == runner_id]  #Only retrieve runner data match with logged in username


    return render_template('runner/my_list.html', my_deliveries=my_deliveries)

@app.route('/runner_choose/<order_id>', methods=['POST'])
def runner_choose(order_id):
    if "username" not in session or session.get("role") != "runner":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    runner_username = session["username"]

    orders = load_json(orders_file)
    deliveries = load_json(delivery_file)
    runners = load_json(runner_file)

    runner = next((r for r in runners if r["username"] == runner_username), None)

    if not runner:
        flash("Runner not found", "danger")
        return redirect(url_for("signin"))

    order_to_transfer = None

    for order in orders:
        if order['id'] == int(order_id) and order['status'] == 'delivery': #Check ID and status
            order_to_transfer = order  # Copy the order
            order['status'] = 'in transit' # Update status on orders.json
            order['runner_id'] = runner["id"] # <---- ADD THIS LINE: Add runner_id to the order
            break

    if order_to_transfer:
        # Add a copy of the order to deliveries
        delivery_copy = order_to_transfer.copy()
        delivery_copy['runner_id'] = runner["id"] #Set the runner
        deliveries.append(delivery_copy)

        save_orders(orders) #update orders.json
        save_deliveries(deliveries) #saving deliveries
    return redirect(url_for('runner_dashboard'))

def save_runners(runners): #save runners
    save_json(runner_file, runners)

@app.route('/complete_order/<order_id>', methods=['POST'])
def complete_order(order_id):
    if "username" not in session or session.get("role") != "runner":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    runner_username = session["username"]
    runners = load_json(runner_file)  # Use the defined constant
    runner_index = None

    for i, r in enumerate(runners):
        if r["username"] == runner_username:
            runner = r
            runner_index = i  # Store the index
            break


    if runner_index is None:
        flash("Runner not found", "danger")
        return redirect(url_for("signin"))

    runner_id = runner["id"]

    deliveries = load_deliveries()
    orders = load_orders()
    reviews = load_json(reviews_file)  # Load reviews

    order_id = int(order_id)

    delivery_to_remove = None
    order_to_update = None

    for delivery in deliveries:
        if delivery.get('id') == order_id and delivery.get('runner_id') == runner_id:
            delivery_to_remove = delivery
            break

    if delivery_to_remove:
        for order in orders:
            if order.get('id') == order_id:
                order_to_update = order
                break

    if delivery_to_remove and order_to_update:
        order_to_update['status'] = 'completed'  # Update status
        deliveries.remove(delivery_to_remove)      # Remove delivery

        # Create a review entry, mirroring the order format
        review = order_to_update.copy()  # Exact copy of the order

        reviews.append(review)

        save_deliveries(deliveries)
        save_orders(orders)
        save_json(reviews_file, reviews)  # Save reviews

        # Increment orders_delivered and save
        runners[runner_index]['orders_delivered'] += 1 #Increment the correct runner
        if save_json(runner_file, runners):  # Save changes to runner.json
            flash("Order completed successfully!", "success")
        else:
            flash("Order completed, but error updating runner data.", "warning")


    else:
        flash("Order not found or not assigned to you.", "danger")

    return redirect(url_for('my_list'))

@app.route('/remove_delivery/<order_id>', methods=['POST'])
def remove_delivery(order_id):
    if "username" not in session or session.get("role") != "runner":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("signin"))

    runner_username = session["username"]
    runners = load_json(runner_file)

    runner = next((r for r in runners if r["username"] == runner_username), None)

    if not runner:
        flash("Runner not found", "danger")
        return redirect(url_for("signin"))

    runner_id = runner["id"]

    deliveries = load_deliveries()
    orders = load_orders()

    order_id = int(order_id)

    delivery_to_remove = None
    order_to_update = None

    for delivery in deliveries:
        if delivery.get('id') == order_id and delivery.get('runner_id') == runner_id:
            delivery_to_remove = delivery
            break

    if delivery_to_remove:
        for order in orders:
            if order.get('id') == order_id:
                order_to_update = order
                break

    if delivery_to_remove and order_to_update:
        order_to_update['status'] = 'delivery'  # Update status
        deliveries.remove(delivery_to_remove)      # Remove delivery

        save_deliveries(deliveries)
        save_orders(orders)
        flash("Delivery removed and order status updated!", "success")
    else:
        flash("Delivery not found or not assigned to you.", "danger")

    return redirect(url_for('my_list'))

if __name__ == '__main__':
     # Ensure the database folder exists
    if not os.path.exists(database_folder):
        os.makedirs(database_folder)

    # Create the required JSON files if they don't exist
    for file_path in [admin_file, buyer_file, seller_file, runner_file,
                      items_file, orders_file, reviews_file, approval_file,
                      cart_file, payment_file]:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump([], f)  # Create empty JSON array

    app.run(debug=True)