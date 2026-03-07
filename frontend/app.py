from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
import requests
import os
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:5001")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
app.secret_key = SECRET_KEY

# Upload configuration
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


def get_api_headers():
    """Get headers with auth token"""
    headers = {}
    if 'token' in session:
        headers['Authorization'] = f"Bearer {session['token']}"
    return headers


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============ Public Routes ============

@app.route("/")
def home():
    """Home page - show public files"""
    try:
        page = request.args.get('page', 1, type=int)
        response = requests.get(f"{BACKEND_URL}/api/search/public", params={'page': page, 'per_page': 12})
        
        if response.status_code == 200:
            data = response.json()
            return render_template('home.html', 
                                 files=data.get('files', []),
                                 pagination=data.get('pagination', {}))
        else:
            return render_template('home.html', files=[], pagination={})
    except Exception as e:
        flash(f"Error loading files: {str(e)}", 'danger')
        return render_template('home.html', files=[], pagination={})


@app.route("/login", methods=["GET", "POST"])
def login():
    """User login"""
    if 'user' in session:
        return redirect(url_for('home'))
    
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        captcha_session_id = request.form.get('captcha_session_id')
        captcha_answer = request.form.get('captcha_answer')
        
        try:
            # Prepare form data
            form_data = {
                'username': username,
                'password': password,
                'captcha_session_id': captcha_session_id,
                'captcha_answer': captcha_answer
            }
            
            response = requests.post(f"{BACKEND_URL}/api/auth/login", data=form_data)
            
            if response.status_code == 200:
                data = response.json()
                session['token'] = data['token']
                session['user'] = data['user']
                session['user_id'] = data['user']['id']
                session['username'] = data['user']['username']
                session['is_admin'] = data['user'].get('is_admin', False)
                
                flash(f"Welcome back, {data['user']['username']}!", 'success')
                return redirect(url_for('home'))
            else:
                error = response.json().get('error', 'Login failed')
                flash(error, 'danger')
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
        
        # Get new captcha
        try:
            captcha_response = requests.get(f"{BACKEND_URL}/api/auth/captcha")
            captcha_data = captcha_response.json() if captcha_response.status_code == 200 else {}
        except:
            captcha_data = {}
        
        return render_template('login.html',
                             captcha_session_id=captcha_data.get('session_id', ''),
                             captcha_image=captcha_data.get('image', ''),
                             backend_url=BACKEND_URL)

    # GET - show login form with captcha
    try:
        captcha_response = requests.get(f"{BACKEND_URL}/api/auth/captcha")
        captcha_data = captcha_response.json() if captcha_response.status_code == 200 else {}
    except:
        captcha_data = {}

    return render_template('login.html',
                         captcha_session_id=captcha_data.get('session_id', ''),
                         captcha_image=captcha_data.get('image', ''),
                         backend_url=BACKEND_URL)


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration"""
    if 'user' in session:
        return redirect(url_for('home'))
    
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        captcha_session_id = request.form.get('captcha_session_id')
        captcha_answer = request.form.get('captcha_answer')
        
        # Handle profile photo
        profile_photo = request.files.get('profile_photo')
        files = {}
        if profile_photo and profile_photo.filename:
            files['profile_photo'] = profile_photo
        
        try:
            form_data = {
                'username': username,
                'email': email,
                'password': password,
                'confirm_password': confirm_password,
                'captcha_session_id': captcha_session_id,
                'captcha_answer': captcha_answer
            }
            
            response = requests.post(f"{BACKEND_URL}/api/auth/register", data=form_data, files=files)
            
            if response.status_code == 201:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                error = response.json().get('error', 'Registration failed')
                flash(error, 'danger')
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
        
        # Get new captcha
        try:
            captcha_response = requests.get(f"{BACKEND_URL}/api/auth/captcha")
            captcha_data = captcha_response.json() if captcha_response.status_code == 200 else {}
        except:
            captcha_data = {}
        
        return render_template('register.html',
                             captcha_session_id=captcha_data.get('session_id', ''),
                             captcha_image=captcha_data.get('image', ''),
                             backend_url=BACKEND_URL)

    # GET - show registration form with captcha
    try:
        captcha_response = requests.get(f"{BACKEND_URL}/api/auth/captcha")
        captcha_data = captcha_response.json() if captcha_response.status_code == 200 else {}
    except:
        captcha_data = {}

    return render_template('register.html',
                         captcha_session_id=captcha_data.get('session_id', ''),
                         captcha_image=captcha_data.get('image', ''),
                         backend_url=BACKEND_URL)


@app.route("/logout")
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))


# ============ User Routes ============

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page"""
    if request.method == "POST":
        action = request.form.get('action')
        
        if action == 'update_profile':
            try:
                form_data = {
                    'username': request.form.get('username'),
                    'email': request.form.get('email')
                }
                
                profile_photo = request.files.get('profile_photo')
                files = {}
                if profile_photo and profile_photo.filename:
                    files['profile_photo'] = profile_photo
                
                response = requests.put(
                    f"{BACKEND_URL}/api/users/me",
                    data=form_data,
                    files=files,
                    headers=get_api_headers()
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        session['username'] = data['user']['username']
                        # Update profile photo in session
                        if 'profile_photo' in data['user']:
                            session['user']['profile_photo'] = data['user']['profile_photo']
                        session.modified = True
                        flash('Profile updated successfully!', 'success')
                        return redirect(url_for('settings'))
                    except Exception as e:
                        flash(f'Error parsing response: {str(e)}', 'danger')
                else:
                    try:
                        error = response.json().get('error', 'Update failed')
                    except:
                        error = f'Server error: {response.status_code}'
                    flash(error, 'danger')
            except Exception as e:
                flash(f"Error: {str(e)}", 'danger')
        
        elif action == 'change_password':
            try:
                form_data = {
                    'current_password': request.form.get('current_password'),
                    'new_password': request.form.get('new_password'),
                    'confirm_password': request.form.get('confirm_password')
                }
                
                response = requests.put(
                    f"{BACKEND_URL}/api/users/me/password",
                    data=form_data,
                    headers=get_api_headers()
                )
                
                if response.status_code == 200:
                    flash('Password changed successfully!', 'success')
                else:
                    error = response.json().get('error', 'Password change failed')
                    flash(error, 'danger')
            except Exception as e:
                flash(f"Error: {str(e)}", 'danger')
        
        elif action == 'delete_photo':
            try:
                response = requests.delete(
                    f"{BACKEND_URL}/api/users/me/photo",
                    headers=get_api_headers()
                )
                
                if response.status_code == 200:
                    flash('Profile photo deleted', 'success')
                else:
                    error = response.json().get('error', 'Delete failed')
                    flash(error, 'danger')
            except Exception as e:
                flash(f"Error: {str(e)}", 'danger')
        
        return redirect(url_for('settings'))
    
    return render_template('settings.html')


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Upload file page"""
    if request.method == "POST":
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        filename = request.form.get('filename')
        category = request.form.get('category')
        visibility = request.form.get('visibility', 'private')
        
        if not file.filename:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if not filename:
            flash('Filename is required', 'danger')
            return redirect(request.url)
        
        if not category:
            flash('Category is required', 'danger')
            return redirect(request.url)
        
        try:
            files = {'file': (file.filename, file, file.content_type)}
            form_data = {
                'filename': filename,
                'category': category,
                'visibility': visibility
            }
            
            response = requests.post(
                f"{BACKEND_URL}/api/files/upload",
                data=form_data,
                files=files,
                headers=get_api_headers()
            )
            
            if response.status_code == 201:
                flash('File uploaded successfully!', 'success')
                return redirect(url_for('my_files'))
            else:
                error = response.json().get('error', 'Upload failed')
                flash(error, 'danger')
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
        
        return redirect(request.url)
    
    return render_template('upload.html')


@app.route("/my-files")
@login_required
def my_files():
    """User's files page"""
    try:
        page = request.args.get('page', 1, type=int)
        category = request.args.get('category', '')
        visibility = request.args.get('visibility', '')

        params = {'page': page, 'per_page': 12}
        if category:
            params['category'] = category
        if visibility:
            params['visibility'] = visibility

        response = requests.get(
            f"{BACKEND_URL}/api/files/my-files",
            params=params,
            headers=get_api_headers()
        )

        if response.status_code == 200:
            data = response.json()
            return render_template('my_files.html',
                                 files=data.get('files', []),
                                 pagination=data.get('pagination', {}))
        else:
            flash('Error loading files', 'danger')
            return render_template('my_files.html', files=[], pagination={})
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('my_files.html', files=[], pagination={})


@app.route("/shared-with-me")
@login_required
def shared_with_me():
    """Files shared with user"""
    try:
        page = request.args.get('page', 1, type=int)
        query = request.args.get('q', '')
        category = request.args.get('category', '')

        params = {'page': page, 'per_page': 12}
        if query:
            params['q'] = query
        if category:
            params['category'] = category

        response = requests.get(
            f"{BACKEND_URL}/api/files/shared-with-me",
            params=params,
            headers=get_api_headers()
        )

        if response.status_code == 200:
            data = response.json()
            return render_template('shared_with_me.html',
                                 files=data.get('files', []),
                                 pagination=data.get('pagination', {}),
                                 query=query)
        else:
            flash('Error loading shared files', 'danger')
            return render_template('shared_with_me.html', files=[], pagination={})
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('shared_with_me.html', files=[], pagination={})


@app.route("/file/<int:file_id>")
@login_required
def view_file(file_id):
    """View file details"""
    try:
        # Check if this is a shared file access
        is_shared = request.args.get('shared', 'false').lower() == 'true'
        
        response = requests.get(
            f"{BACKEND_URL}/api/files/{file_id}",
            headers=get_api_headers()
        )

        if response.status_code == 200:
            data = response.json()
            return render_template('file_detail.html', file=data.get('file', {}))
        elif is_shared:
            # If shared access failed, try to find via shared files
            flash('This file was shared with you, but you may not have access anymore', 'warning')
        else:
            flash('File not found', 'danger')
        return redirect(url_for('my_files'))
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('my_files'))


@app.route("/file/<int:file_id>/download")
@login_required
def download_file(file_id):
    """Download file"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/files/{file_id}/download",
            headers=get_api_headers(),
            stream=True
        )

        if response.status_code == 200:
            from flask import Response
            # Get filename from Content-Disposition header
            content_disp = response.headers.get('Content-Disposition', '')
            filename = 'download'
            if 'filename=' in content_disp:
                filename = content_disp.split('filename=')[1].strip('"')
            
            return Response(
                response.content,
                status=200,
                headers={
                    'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': response.headers.get('Content-Length', len(response.content))
                }
            )
        else:
            flash('Download failed', 'danger')
            return redirect(url_for('my_files'))
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('my_files'))


@app.route("/file/<int:file_id>/delete", methods=["POST"])
@login_required
def delete_file(file_id):
    """Delete file"""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/api/files/{file_id}",
            headers=get_api_headers()
        )
        
        if response.status_code == 200:
            flash('File deleted successfully', 'success')
        else:
            error = response.json().get('error', 'Delete failed')
            flash(error, 'danger')
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
    
    return redirect(url_for('my_files'))


@app.route("/file/<int:file_id>/edit", methods=["GET", "POST"])
@login_required
def edit_file(file_id):
    """Edit file metadata"""
    if request.method == "POST":
        try:
            form_data = {
                'filename': request.form.get('filename'),
                'category': request.form.get('category'),
                'visibility': request.form.get('visibility')
            }

            response = requests.put(
                f"{BACKEND_URL}/api/files/{file_id}",
                data=form_data,
                headers=get_api_headers()
            )

            if response.status_code == 200:
                flash('File updated successfully!', 'success')
                return redirect(url_for('view_file', file_id=file_id))
            else:
                try:
                    error = response.json().get('error', 'Update failed')
                except:
                    error = f'Server error: {response.status_code}'
                flash(error, 'danger')
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')

    try:
        response = requests.get(
            f"{BACKEND_URL}/api/files/{file_id}",
            headers=get_api_headers()
        )

        if response.status_code == 200:
            try:
                data = response.json()
                return render_template('file_edit.html', file=data.get('file', {}))
            except Exception as e:
                flash(f'Error parsing file data: {str(e)}', 'danger')
                return redirect(url_for('my_files'))
        else:
            flash('File not found', 'danger')
            return redirect(url_for('my_files'))
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('my_files'))


@app.route("/file/<int:file_id>/share", methods=["GET", "POST"])
@login_required
def share_file(file_id):
    """Share file with another user"""
    if request.method == "POST":
        try:
            form_data = {
                'username': request.form.get('username')
            }

            response = requests.post(
                f"{BACKEND_URL}/api/files/{file_id}/share",
                data=form_data,
                headers=get_api_headers()
            )

            if response.status_code == 200:
                flash('File shared successfully!', 'success')
                return redirect(url_for('view_file', file_id=file_id))
            else:
                error = response.json().get('error', 'Share failed')
                flash(error, 'danger')
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')

    try:
        response = requests.get(
            f"{BACKEND_URL}/api/files/{file_id}",
            headers=get_api_headers()
        )

        if response.status_code == 200:
            data = response.json()
            return render_template('file_share.html', file=data.get('file', {}))
        else:
            flash('File not found', 'danger')
            return redirect(url_for('my_files'))
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('my_files'))


@app.route("/s/<share_token>")
def get_shared_file(share_token):
    """View shared file by token (public access)"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/files/shared/{share_token}",
            headers=get_api_headers()
        )

        if response.status_code == 200:
            data = response.json()
            return render_template('shared_file.html', file=data.get('file', {}))
        else:
            flash('File not found or no longer shared', 'danger')
            return redirect(url_for('home'))
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('home'))


@app.route("/search")
@login_required
def search():
    """Search public files"""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        page = request.args.get('page', 1, type=int)

        params = {'page': page, 'per_page': 12}
        # Send query param even if empty (for proper filtering)
        params['q'] = query if query else ''
        # Only add category if it's not empty
        if category and category.strip():
            params['category'] = category

        # Use public search endpoint - only shows public files
        response = requests.get(
            f"{BACKEND_URL}/api/search/public",
            params=params,
            headers=get_api_headers()
        )

        if response.status_code == 200:
            data = response.json()
            return render_template('search.html',
                                 files=data.get('files', []),
                                 pagination=data.get('pagination', {}),
                                 query=query)
        else:
            return render_template('search.html', files=[], pagination={}, query=query)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('search.html', files=[], pagination={}, query=query)


# ============ Admin Routes ============

@app.route("/admin")
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/admin/dashboard",
            headers=get_api_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            return render_template('admin/dashboard.html',
                                 stats=data.get('stats', {}),
                                 recent_activity=data.get('recent_activity', []),
                                 top_users=data.get('top_users', []))
        else:
            flash('Error loading dashboard', 'danger')
            return render_template('admin/dashboard.html', stats={}, recent_activity=[], top_users=[])
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('admin/dashboard.html', stats={}, recent_activity=[], top_users=[])


@app.route("/admin/users")
@admin_required
def admin_users():
    """Admin users management"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        
        params = {'page': page, 'per_page': 20}
        if search:
            params['search'] = search
        if status:
            params['status'] = status
        
        response = requests.get(
            f"{BACKEND_URL}/api/admin/users",
            params=params,
            headers=get_api_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            return render_template('admin/users.html',
                                 users=data.get('users', []),
                                 pagination=data.get('pagination', {}))
        else:
            return render_template('admin/users.html', users=[], pagination={})
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('admin/users.html', users=[], pagination={})


@app.route("/admin/users/<int:user_id>")
@admin_required
def admin_user_detail(user_id):
    """Admin user detail page"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/admin/users/{user_id}",
            headers=get_api_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            return render_template('admin/user_detail.html',
                                 user=data.get('user', {}),
                                 files=data.get('files', []),
                                 logs=data.get('recent_logs', []))
        else:
            flash('User not found', 'danger')
            return redirect(url_for('admin_users'))
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('admin_users'))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    """Admin delete user"""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/api/admin/users/{user_id}",
            headers=get_api_headers()
        )
        
        if response.status_code == 200:
            flash('User deleted successfully', 'success')
        else:
            error = response.json().get('error', 'Delete failed')
            flash(error, 'danger')
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
    
    return redirect(url_for('admin_users'))


@app.route("/admin/files")
@admin_required
def admin_files():
    """Admin files management"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        visibility = request.args.get('visibility', '')
        
        params = {'page': page, 'per_page': 20}
        if search:
            params['search'] = search
        if visibility:
            params['visibility'] = visibility
        
        response = requests.get(
            f"{BACKEND_URL}/api/admin/files",
            params=params,
            headers=get_api_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            return render_template('admin/files.html',
                                 files=data.get('files', []),
                                 pagination=data.get('pagination', {}))
        else:
            return render_template('admin/files.html', files=[], pagination={})
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('admin/files.html', files=[], pagination={})


@app.route("/admin/files/<int:file_id>/delete", methods=["POST"])
@admin_required
def admin_delete_file(file_id):
    """Admin delete file"""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/api/admin/files/{file_id}",
            headers=get_api_headers()
        )
        
        if response.status_code == 200:
            flash('File deleted successfully', 'success')
        else:
            error = response.json().get('error', 'Delete failed')
            flash(error, 'danger')
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
    
    return redirect(url_for('admin_files'))


@app.route("/admin/logs")
@admin_required
def admin_logs():
    """Admin activity logs"""
    try:
        page = request.args.get('page', 1, type=int)
        action = request.args.get('action', '')
        status = request.args.get('status', '')

        params = {'page': page, 'per_page': 50}
        if action:
            params['action'] = action
        if status:
            params['status'] = status

        response = requests.get(
            f"{BACKEND_URL}/api/admin/logs",
            params=params,
            headers=get_api_headers()
        )

        if response.status_code == 200:
            data = response.json()
            return render_template('admin/logs.html',
                                 logs=data.get('logs', []),
                                 pagination=data.get('pagination', {}))
        else:
            return render_template('admin/logs.html', logs=[], pagination={})
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('admin/logs.html', logs=[], pagination={})


# ============ API Proxy Routes (for images and static assets) ============

@app.route("/api/files/image/<path:object_path>", methods=["GET"])
def proxy_image(object_path):
    """Proxy image requests to backend API"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/files/image/{object_path}",
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            from flask import Response
            return Response(
                response.content,
                status=200,
                headers={
                    'Content-Type': response.headers.get('Content-Type', 'image/jpeg'),
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            # Return placeholder image on error
            return Response(
                b'',
                status=404,
                headers={'Content-Type': 'image/jpeg'}
            )
    except Exception as e:
        return Response(b'', status=500)


@app.route("/api/files/shared/<share_token>/download", methods=["GET"])
def proxy_shared_download(share_token):
    """Proxy shared file download to backend API"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/files/shared/{share_token}/download",
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            from flask import Response
            content_disp = response.headers.get('Content-Disposition', '')
            filename = 'download'
            if 'filename=' in content_disp:
                filename = content_disp.split('filename=')[1].strip('"')
            
            return Response(
                response.content,
                status=200,
                headers={
                    'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': response.headers.get('Content-Length', len(response.content))
                }
            )
        else:
            flash('Download failed', 'danger')
            return redirect(url_for('home'))
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('home'))


@app.route("/api/files/notifications", methods=["GET"])
@login_required
def proxy_notifications():
    """Proxy notifications endpoint to backend API"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/files/notifications",
            headers=get_api_headers(),
            timeout=10
        )
        return response.json()
    except Exception as e:
        return jsonify({"notifications": [], "unread_count": 0, "error": str(e)})


@app.route("/api/files/notifications/mark-read", methods=["POST"])
@login_required
def proxy_mark_read():
    """Proxy mark notifications as read to backend API"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/files/notifications/mark-read",
            headers=get_api_headers(),
            timeout=10
        )
        return response.json()
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_ENV") == "development")
