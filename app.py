from flask import Flask,render_template,request,redirect,url_for,session,jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "order_secret_key"

client = MongoClient("mongodb+srv://raufurrahman2020_db_user:1234567890@cluster0.kiwhfsx.mongodb.net/?appName=Cluster0")
db = client["order_management"]

orders = db["orders"]
customers = db["customers"]
categories = db["categories"]
models = db["models"]
brands = db["brands"]
employees = db["employees"]
roles = db["roles"]
accounts = db["accounts"]


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login',methods=['POST'])
def login():

    username=request.form['username']
    password=request.form['password']

    if username=="admin" and password=="admin":
        session['role']="admin"
        return redirect('/admin/dashboard')

    elif username=="employee" and password=="employee":
        session['role']="employee"
        return redirect('/employee/dashboard')

    return "Invalid Credentials"


# ---------------- ADMIN ----------------

@app.route('/admin/dashboard')
def admin_dashboard():

    pending=list(
        orders.find({"status":"Pending"})
    )

    completed=list(
        orders.find({"status":"Completed"})
    )

    # Group pending orders by customer phone
    pending_customers = {}
    for order in pending:
        phone = order['phone']
        if phone not in pending_customers:
            pending_customers[phone] = {
                'customer_name': order['customer_name'],
                'address': order['address'],
                'orders': []
            }
        pending_customers[phone]['orders'].append(order)

    # Group completed orders by customer phone
    completed_customers = {}
    for order in completed:
        phone = order['phone']
        if phone not in completed_customers:
            completed_customers[phone] = {
                'customer_name': order['customer_name'],
                'address': order['address'],
                'orders': []
            }
        completed_customers[phone]['orders'].append(order)

    # Calculate total value of pending orders
    pending_orders_value = sum(order.get('total_amount', 0) for order in pending)

    return render_template(
        'admin/dashboard.html',
        pending=pending,
        completed=completed,
        pending_customers=pending_customers,
        completed_customers=completed_customers,
        pending_orders_value=pending_orders_value
    )


@app.route('/admin/pending')
def pending_orders():

    pending=list(
        orders.find({"status":"Pending"}).sort("_id", -1)
    )

    # Group pending orders by customer phone
    pending_customers = {}
    for order in pending:
        phone = order['phone']
        if phone not in pending_customers:
            pending_customers[phone] = {
                'customer_name': order['customer_name'],
                'address': order['address'],
                'orders': []
            }
        pending_customers[phone]['orders'].append(order)

    return render_template(
        'admin/pending_orders.html',
        pending_customers=pending_customers
    )


@app.route('/admin/completed')
def completed_orders():

    completed=list(
        orders.find({"status":"Completed"}).sort("_id", -1)
    )

    # Group completed orders by customer phone
    completed_customers = {}
    for order in completed:
        phone = order['phone']
        if phone not in completed_customers:
            completed_customers[phone] = {
                'customer_name': order['customer_name'],
                'address': order['address'],
                'orders': []
            }
        completed_customers[phone]['orders'].append(order)

    return render_template(
        'admin/completed_orders.html',
        completed_customers=completed_customers
    )


@app.route('/admin/customers')
def view_customers():

    # Get unique customers by phone number
    all_customers = list(customers.find())
    unique_customers = {}
    
    for customer in all_customers:
        phone = customer['phone']
        if phone not in unique_customers:
            unique_customers[phone] = customer
    
    customers_list = list(unique_customers.values())

    return render_template(
        'admin/customers.html',
        customers=customers_list
    )


@app.route('/api/customer/<phone>')
def get_customer_by_phone(phone):
    customer = customers.find_one({'phone': phone})
    if customer:
        return jsonify({
            'customer_name': customer.get('customer_name', ''),
            'address': customer.get('address', '')
        })
    return jsonify(None)


@app.route('/add_order',methods=['GET','POST'])
def add_order():

    if request.method=="POST":

        customer_name=request.form['customer_name']
        phone=request.form['phone']
        address=request.form['address']
        parcel_details=request.form.get('parcel_details', '')

        # Process billing items
        billing_items = []
        total_amount = 0

        # Get all form keys to find billing rows
        form_keys = list(request.form.keys())
        row_indices = set()

        for key in form_keys:
            if key.startswith('category_'):
                row_index = key.split('_')[1]
                row_indices.add(row_index)

        for idx in row_indices:
            category_id = request.form.get(f'category_{idx}', '')
            brand_id = request.form.get(f'brand_{idx}', '')
            model = request.form.get(f'model_{idx}', '')
            quantity = request.form.get(f'quantity_{idx}', '0')
            rate = request.form.get(f'rate_{idx}', '0')
            amount = request.form.get(f'amount_{idx}', '0')

            if category_id and model and quantity and rate:
                # Convert category ID to category name
                category_obj = categories.find_one({'_id': ObjectId(category_id)})
                category_name = category_obj['name'] if category_obj else category_id

                # Convert brand ID to brand name
                brand_name = ''
                if brand_id:
                    brand_obj = brands.find_one({'_id': ObjectId(brand_id)})
                    brand_name = brand_obj['name'] if brand_obj else brand_id

                billing_items.append({
                    "category": category_name,
                    "brand": brand_name,
                    "model": model,
                    "quantity": int(quantity),
                    "rate": float(rate),
                    "amount": float(amount),
                    "supplied": False
                })
                total_amount += float(amount)

        # Determine primary category (first item's category or general)
        primary_category = billing_items[0]['category'] if billing_items else 'General'

        customer={
            "customer_name":customer_name,
            "phone":phone,
            "address":address
        }

        customers.insert_one(customer)

        order={
            "customer_name":customer_name,
            "phone":phone,
            "address":address,
            "category":primary_category,
            "billing_items":billing_items,
            "total_amount":total_amount,
            "parcel_details":parcel_details,
            "status":"Pending"
        }

        orders.insert_one(order)

        return redirect('/admin/pending')

    category_list = list(categories.find())
    model_list = list(models.find())
    brand_list = list(brands.find())

    # Convert ObjectId to string for JSON serialization
    for category in category_list:
        category['_id'] = str(category['_id'])

    for model in model_list:
        model['_id'] = str(model['_id'])
        if 'category_id' in model:
            model['category_id'] = str(model['category_id'])

    for brand in brand_list:
        brand['_id'] = str(brand['_id'])
        if 'category_id' in brand:
            brand['category_id'] = str(brand['category_id'])

    return render_template(
        'admin/add_order.html',
        categories=category_list,
        models=model_list,
        brands=brand_list
    )


@app.route('/delete/<id>')
def delete_order(id):

    orders.delete_one({
        "_id":ObjectId(id)
    })

    # Redirect back to the referring page
    referrer = request.referrer
    if referrer and '/admin/completed' in referrer:
        return redirect('/admin/completed')
    return redirect('/admin/pending')


@app.route('/complete/<id>')
def complete_order(id):

    orders.update_one(
        {"_id":ObjectId(id)},
        {
            "$set":
            {
                "status":"Completed"
            }
        }
    )

    return redirect('/admin/pending')


@app.route('/reverse/<id>')
def reverse_order(id):

    orders.update_one(
        {"_id":ObjectId(id)},
        {
            "$set":
            {
                "status":"Pending"
            }
        }
    )

    return redirect('/admin/completed')


@app.route('/edit_customer/<id>',methods=['GET','POST'])
def edit_customer(id):

    customer=customers.find_one({
        "_id":ObjectId(id)
    })

    if request.method=="POST":

        customers.update_one(
            {"_id":ObjectId(id)},
            {
                "$set":
                {
                    "customer_name":request.form['customer_name'],
                    "phone":request.form['phone'],
                    "address":request.form['address']
                }
            }
        )

        return redirect('/admin/customers')

    return render_template(
        'admin/edit_customer.html',
        customer=customer
    )


@app.route('/delete_customer/<id>')
def delete_customer(id):

    customers.delete_one({
        "_id":ObjectId(id)
    })

    return redirect('/admin/customers')


@app.route('/view_order/<id>')
def view_order(id):

    order=orders.find_one({
        "_id":ObjectId(id)
    })

    # Calculate total_amount if it doesn't exist (for legacy orders)
    if order and 'total_amount' not in order:
        total = 0
        if 'billing_items' in order:
            for item in order['billing_items']:
                total += item.get('amount', 0)
        order['total_amount'] = total

    return render_template(
        'admin/view_order.html',
        order=order
    )


@app.route('/customer_orders/<phone>')
def customer_orders(phone):

    customer_orders_list=list(
        orders.find({"phone":phone}).sort("_id", -1)
    )

    customer=customers.find_one({"phone":phone})

    # Calculate total_amount for legacy orders
    for order in customer_orders_list:
        if 'total_amount' not in order:
            total = 0
            if 'billing_items' in order:
                for item in order['billing_items']:
                    total += item.get('amount', 0)
            order['total_amount'] = total

    return render_template(
        'admin/customer_orders.html',
        orders=customer_orders_list,
        customer=customer
    )


@app.route('/toggle_supplied/<order_id>/<int:item_index>', methods=['POST'])
def toggle_supplied(order_id, item_index):
    order = orders.find_one({"_id": ObjectId(order_id)})
    if order and 'billing_items' in order and item_index < len(order['billing_items']):
        billing_items = order['billing_items']
        # Ensure supplied field exists
        if 'supplied' not in billing_items[item_index]:
            billing_items[item_index]['supplied'] = False
        # Toggle the supplied status
        billing_items[item_index]['supplied'] = not billing_items[item_index]['supplied']
        # Update the order
        orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"billing_items": billing_items}}
        )
        return jsonify({"success": True, "supplied": billing_items[item_index]['supplied']})
    return jsonify({"success": False}), 400


@app.route('/edit/<id>',methods=['GET','POST'])
def edit_order(id):

    order=orders.find_one({
        "_id":ObjectId(id)
    })

    if request.method=="POST":

        customer_name=request.form['customer_name']
        phone=request.form['phone']
        address=request.form['address']
        parcel_details=request.form.get('parcel_details', '')

        # Process billing items
        billing_items = []
        total_amount = 0

        # Get all form keys to find billing rows
        form_keys = list(request.form.keys())
        row_indices = set()

        for key in form_keys:
            if key.startswith('category_'):
                row_index = key.split('_')[1]
                row_indices.add(row_index)

        for idx in row_indices:
            category_id = request.form.get(f'category_{idx}', '')
            brand_id = request.form.get(f'brand_{idx}', '')
            model = request.form.get(f'model_{idx}', '')
            quantity = request.form.get(f'quantity_{idx}', '0')
            rate = request.form.get(f'rate_{idx}', '0')
            amount = request.form.get(f'amount_{idx}', '0')

            if category_id and model and quantity and rate:
                # Convert category ID to category name
                category_obj = categories.find_one({'_id': ObjectId(category_id)})
                category_name = category_obj['name'] if category_obj else category_id

                # Convert brand ID to brand name
                brand_name = ''
                if brand_id:
                    brand_obj = brands.find_one({'_id': ObjectId(brand_id)})
                    brand_name = brand_obj['name'] if brand_obj else brand_id

                billing_items.append({
                    "category": category_name,
                    "brand": brand_name,
                    "model": model,
                    "quantity": int(quantity),
                    "rate": float(rate),
                    "amount": float(amount),
                    "supplied": False
                })
                total_amount += float(amount)

        # Determine primary category (first item's category or general)
        primary_category = billing_items[0]['category'] if billing_items else 'General'

        orders.update_one(
            {"_id":ObjectId(id)},
            {
                "$set":
                {
                    "customer_name": customer_name,
                    "phone": phone,
                    "address": address,
                    "category": primary_category,
                    "billing_items": billing_items,
                    "total_amount": total_amount,
                    "parcel_details": parcel_details
                }
            }
        )

        return redirect('/admin/pending')

    category_list = list(categories.find())
    model_list = list(models.find())
    brand_list = list(brands.find())

    # Convert ObjectId to string for JSON serialization
    for category in category_list:
        category['_id'] = str(category['_id'])

    for model in model_list:
        model['_id'] = str(model['_id'])
        if 'category_id' in model:
            model['category_id'] = str(model['category_id'])

    for brand in brand_list:
        brand['_id'] = str(brand['_id'])
        if 'category_id' in brand:
            brand['category_id'] = str(brand['category_id'])

    return render_template(
        'admin/edit_order.html',
        order=order,
        categories=category_list,
        models=model_list,
        brands=brand_list
    )


# ---------------- CATEGORY MANAGEMENT ----------------

@app.route('/admin/categories')
def manage_categories():
    category_list = list(categories.find())
    return render_template('admin/categories.html', categories=category_list)


@app.route('/admin/category/add', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        category_name = request.form['category_name']
        if category_name:
            categories.insert_one({'name': category_name})
        return redirect('/admin/categories')
    return render_template('admin/add_category.html')


@app.route('/admin/category/edit/<id>', methods=['GET', 'POST'])
def edit_category(id):
    category = categories.find_one({'_id': ObjectId(id)})
    if request.method == 'POST':
        categories.update_one(
            {'_id': ObjectId(id)},
            {'$set': {'name': request.form['category_name']}}
        )
        return redirect('/admin/categories')
    return render_template('admin/edit_category.html', category=category)


@app.route('/admin/category/delete/<id>')
def delete_category(id):
    categories.delete_one({'_id': ObjectId(id)})
    return redirect('/admin/categories')


# ---------------- MODEL MANAGEMENT ----------------

@app.route('/admin/models')
def manage_models():
    model_list = list(models.find())
    category_list = list(categories.find())
    return render_template('admin/models.html', models=model_list, categories=category_list)


@app.route('/admin/model/add', methods=['GET', 'POST'])
def add_model():
    category_list = list(categories.find())
    if request.method == 'POST':
        model_name = request.form['model_name']
        category_id = request.form['category_id']
        if model_name and category_id:
            category = categories.find_one({'_id': ObjectId(category_id)})
            models.insert_one({
                'name': model_name,
                'category_id': ObjectId(category_id),
                'category_name': category['name'] if category else ''
            })
        return redirect('/admin/models')
    return render_template('admin/add_model.html', categories=category_list)


@app.route('/admin/model/edit/<id>', methods=['GET', 'POST'])
def edit_model(id):
    model = models.find_one({'_id': ObjectId(id)})
    category_list = list(categories.find())
    if request.method == 'POST':
        category_id = request.form['category_id']
        category = categories.find_one({'_id': ObjectId(category_id)})
        models.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'name': request.form['model_name'],
                'category_id': ObjectId(category_id),
                'category_name': category['name'] if category else ''
            }}
        )
        return redirect('/admin/models')
    return render_template('admin/edit_model.html', model=model, categories=category_list)


@app.route('/admin/model/delete/<id>')
def delete_model(id):
    models.delete_one({'_id': ObjectId(id)})
    return redirect('/admin/models')


# ---------------- BRAND MANAGEMENT ----------------

@app.route('/admin/brands')
def manage_brands():
    category_id = request.args.get('category_id')
    category_list = list(categories.find())

    # Convert ObjectId to string for JSON serialization
    for category in category_list:
        category['_id'] = str(category['_id'])

    if category_id:
        brand_list = list(brands.find({'category_id': ObjectId(category_id)}))
    else:
        brand_list = list(brands.find())

    # Populate category names for brands and convert ObjectIds to strings
    for brand in brand_list:
        brand['_id'] = str(brand['_id'])
        if 'category_id' in brand and brand['category_id']:
            brand['category_id'] = str(brand['category_id'])
            category = categories.find_one({'_id': ObjectId(brand['category_id'])})
            brand['category_name'] = category['name'] if category else ''
        else:
            brand['category_name'] = ''

    return render_template('admin/brands.html', brands=brand_list, categories=category_list, selected_category=category_id)


@app.route('/admin/brand/add', methods=['GET', 'POST'])
def add_brand():
    category_list = list(categories.find())
    if request.method == 'POST':
        brand_name = request.form['brand_name']
        category_id = request.form['category_id']
        if brand_name and category_id:
            category = categories.find_one({'_id': ObjectId(category_id)})
            brands.insert_one({
                'name': brand_name,
                'category_id': ObjectId(category_id),
                'category_name': category['name'] if category else ''
            })
        return redirect('/admin/brands')
    return render_template('admin/add_brand.html', categories=category_list)


@app.route('/admin/brand/edit/<id>', methods=['GET', 'POST'])
def edit_brand(id):
    brand = brands.find_one({'_id': ObjectId(id)})
    category_list = list(categories.find())
    if request.method == 'POST':
        category_id = request.form['category_id']
        category = categories.find_one({'_id': ObjectId(category_id)})
        brands.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'name': request.form['brand_name'],
                'category_id': ObjectId(category_id),
                'category_name': category['name'] if category else ''
            }}
        )
        return redirect('/admin/brands')
    return render_template('admin/edit_brand.html', brand=brand, categories=category_list)


@app.route('/admin/brand/delete/<id>')
def delete_brand(id):
    brands.delete_one({'_id': ObjectId(id)})
    return redirect('/admin/brands')


# ---------------- ROLE MANAGEMENT ----------------

@app.route('/admin/roles')
def manage_roles():
    role_list = list(roles.find())
    return render_template('admin/roles.html', roles=role_list)


@app.route('/admin/role/add', methods=['GET', 'POST'])
def add_role():
    if request.method == 'POST':
        role_name = request.form['role_name']
        if role_name:
            roles.insert_one({'name': role_name})
        return redirect('/admin/roles')
    return render_template('admin/add_role.html')


@app.route('/admin/role/edit/<id>', methods=['GET', 'POST'])
def edit_role(id):
    role = roles.find_one({'_id': ObjectId(id)})
    if request.method == 'POST':
        roles.update_one(
            {'_id': ObjectId(id)},
            {'$set': {'name': request.form['role_name']}}
        )
        return redirect('/admin/roles')
    return render_template('admin/edit_role.html', role=role)


@app.route('/admin/role/delete/<id>')
def delete_role(id):
    roles.delete_one({'_id': ObjectId(id)})
    return redirect('/admin/roles')


# ---------------- EMPLOYEE MANAGEMENT ----------------

@app.route('/admin/employees')
def manage_employees():
    employee_list = list(employees.find())
    employee_count = len(employee_list)
    return render_template('admin/employees.html', employees=employee_list, employee_count=employee_count)


@app.route('/admin/employee/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        employee_name = request.form['employee_name']
        phone = request.form['phone']
        role = request.form['role']
        salary_type = request.form['salary_type']
        salary_per_day = request.form.get('salary_per_day', 0)
        address = request.form.get('address', '')
        
        # Handle photo upload
        photo = request.files.get('photo')
        photo_path = ''
        if photo and photo.filename:
            from werkzeug.utils import secure_filename
            import os
            upload_folder = os.path.join('static', 'uploads', 'employees')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(upload_folder, filename)
            photo.save(photo_path)
            # Store path relative to static folder
            photo_path = photo_path.replace('\\', '/')
            if photo_path.startswith('static/'):
                photo_path = photo_path[7:]  # Remove 'static/' prefix
        
        # Handle ID proof upload
        id_proof_file = request.files.get('id_proof')
        id_proof_path = ''
        if id_proof_file and id_proof_file.filename:
            from werkzeug.utils import secure_filename
            import os
            upload_folder = os.path.join('static', 'uploads', 'id_proofs')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(id_proof_file.filename)
            id_proof_path = os.path.join(upload_folder, filename)
            id_proof_file.save(id_proof_path)
            # Store path relative to static folder
            id_proof_path = id_proof_path.replace('\\', '/')
            if id_proof_path.startswith('static/'):
                id_proof_path = id_proof_path[7:]  # Remove 'static/' prefix
        
        employee_data = {
            'employee_name': employee_name,
            'phone': phone,
            'role': role,
            'salary_type': salary_type,
            'salary_per_day': float(salary_per_day) if salary_type == 'per_day' and salary_per_day else 0,
            'id_proof': id_proof_path,
            'address': address,
            'photo': photo_path
        }
        
        employees.insert_one(employee_data)
        return redirect('/admin/employees')
    
    role_list = list(roles.find())
    return render_template('admin/add_employee.html', roles=role_list)


@app.route('/admin/employee/edit/<id>', methods=['GET', 'POST'])
def edit_employee(id):
    employee = employees.find_one({'_id': ObjectId(id)})
    
    if request.method == 'POST':
        employee_name = request.form['employee_name']
        phone = request.form['phone']
        role = request.form['role']
        salary_type = request.form['salary_type']
        salary_per_day = request.form.get('salary_per_day', 0)
        address = request.form.get('address', '')
        
        # Handle photo upload
        photo = request.files.get('photo')
        photo_path = employee.get('photo', '')
        if photo and photo.filename:
            from werkzeug.utils import secure_filename
            import os
            upload_folder = os.path.join('static', 'uploads', 'employees')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(upload_folder, filename)
            photo.save(photo_path)
            # Store path relative to static folder
            photo_path = photo_path.replace('\\', '/')
            if photo_path.startswith('static/'):
                photo_path = photo_path[7:]  # Remove 'static/' prefix
        
        # Handle ID proof upload
        id_proof_file = request.files.get('id_proof')
        id_proof_path = employee.get('id_proof', '')
        if id_proof_file and id_proof_file.filename:
            from werkzeug.utils import secure_filename
            import os
            upload_folder = os.path.join('static', 'uploads', 'id_proofs')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(id_proof_file.filename)
            id_proof_path = os.path.join(upload_folder, filename)
            id_proof_file.save(id_proof_path)
            # Store path relative to static folder
            id_proof_path = id_proof_path.replace('\\', '/')
            if id_proof_path.startswith('static/'):
                id_proof_path = id_proof_path[7:]  # Remove 'static/' prefix
        
        employees.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'employee_name': employee_name,
                'phone': phone,
                'role': role,
                'salary_type': salary_type,
                'salary_per_day': float(salary_per_day) if salary_type == 'per_day' and salary_per_day else 0,
                'id_proof': id_proof_path,
                'address': address,
                'photo': photo_path
            }}
        )
        
        return redirect('/admin/employees')
    
    role_list = list(roles.find())
    return render_template('admin/edit_employee.html', employee=employee, roles=role_list)


@app.route('/admin/employee/delete/<id>')
def delete_employee(id):
    employees.delete_one({'_id': ObjectId(id)})
    return redirect('/admin/employees')


# ---------------- ACCOUNT MANAGEMENT ----------------

@app.route('/admin/accounts/<employee_id>')
def manage_accounts(employee_id):
    employee = employees.find_one({'_id': ObjectId(employee_id)})
    account_list = list(accounts.find({'employee_id': ObjectId(employee_id)}).sort('date', -1))
    return render_template('admin/accounts.html', employee=employee, accounts=account_list)


@app.route('/admin/account/add/<employee_id>', methods=['GET', 'POST'])
def add_account(employee_id):
    employee = employees.find_one({'_id': ObjectId(employee_id)})
    
    if request.method == 'POST':
        date = request.form['date']
        day = request.form['day']
        salary_per_day = request.form.get('salary_per_day', 0)
        advance = request.form.get('advance', 0)
        
        salary_per_day_float = float(salary_per_day) if salary_per_day else 0
        advance_float = float(advance) if advance else 0
        balance = salary_per_day_float - advance_float
        
        account_data = {
            'employee_id': ObjectId(employee_id),
            'employee_name': employee['employee_name'],
            'date': date,
            'day': day,
            'salary_per_day': salary_per_day_float,
            'advance': advance_float,
            'balance': balance,
            'total_salary': balance
        }
        
        accounts.insert_one(account_data)
        return redirect(f'/admin/accounts/{employee_id}')
    
    return render_template('admin/add_account.html', employee=employee)


@app.route('/admin/account/delete/<account_id>/<employee_id>')
def delete_account(account_id, employee_id):
    accounts.delete_one({'_id': ObjectId(account_id)})
    return redirect(f'/admin/accounts/{employee_id}')


@app.route('/admin/accounts/weekly/<employee_id>')
def weekly_report(employee_id):
    employee = employees.find_one({'_id': ObjectId(employee_id)})
    account_list = list(accounts.find({'employee_id': ObjectId(employee_id)}).sort('date', -1))
    
    # Group by week
    weekly_data = {}
    for account in account_list:
        from datetime import datetime
        date_obj = datetime.strptime(account['date'], '%Y-%m-%d')
        week = date_obj.isocalendar()[1]  # Get week number
        year = date_obj.year
        week_key = f"{year}-W{week}"
        
        if week_key not in weekly_data:
            weekly_data[week_key] = {
                'week': week_key,
                'total_salary': 0,
                'total_advance': 0,
                'total_balance': 0,
                'days_worked': 0,
                'accounts': []
            }
        
        weekly_data[week_key]['total_salary'] += account.get('total_salary', 0)
        weekly_data[week_key]['total_advance'] += account.get('advance', 0)
        weekly_data[week_key]['total_balance'] += account.get('balance', 0)
        weekly_data[week_key]['days_worked'] += 1
        weekly_data[week_key]['accounts'].append(account)
    
    weekly_list = list(weekly_data.values())
    weekly_list.sort(key=lambda x: x['week'], reverse=True)
    
    return render_template('admin/weekly_report.html', employee=employee, weekly_data=weekly_list)


# ---------------- EMPLOYEE ----------------

@app.route('/employee/dashboard')
def employee_dashboard():

    data=list(orders.find())

    return render_template(
        'employee/dashboard.html',
        orders=data
    )


@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)