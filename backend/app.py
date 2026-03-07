from flask import Flask, request, jsonify, Response
import requests
import os
from functools import wraps

app = Flask(__name__)

API_URL = os.getenv("API_URL", "http://api:8080")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")


def proxy_request(method, endpoint, **kwargs):
    """Proxy request to API service"""
    url = f"{API_URL}{endpoint}"

    # Prepare request data
    data = None
    files = None
    json_data = None
    headers = {}

    # Forward Authorization header if present
    if "Authorization" in request.headers:
        headers["Authorization"] = request.headers["Authorization"]

    if request.content_type and "multipart/form-data" in request.content_type:
        files = request.files
        data = request.form.to_dict()
    elif request.content_type and "application/json" in request.content_type:
        json_data = request.get_json()
    else:
        # For PUT/DELETE with form data, use get_data() to handle all methods
        data = request.form.to_dict()
        if not data and request.method in ['PUT', 'PATCH', 'DELETE']:
            # Parse form data from raw body for non-POST methods
            from urllib.parse import parse_qs
            raw_data = request.get_data(as_text=True)
            if raw_data:
                parsed = parse_qs(raw_data)
                data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    try:
        # Make request to API with query params
        response = requests.request(
            method=method,
            url=url,
            params=request.args,  # Forward query parameters
            json=json_data,
            data=data,
            files=files,
            headers=headers,
            timeout=300,
            stream=True  # Enable streaming for large files
        )

        # Handle file downloads and images - return as-is
        if (endpoint.endswith("/download") or "/image/" in endpoint) and response.status_code == 200:
            # Build response headers
            response_headers = {}
            if 'Content-Type' in response.headers:
                response_headers['Content-Type'] = response.headers['Content-Type']
            if 'Content-Length' in response.headers:
                response_headers['Content-Length'] = response.headers['Content-Length']
            if 'Cache-Control' in response.headers:
                response_headers['Cache-Control'] = response.headers['Cache-Control']
            if 'Content-Disposition' in response.headers:
                response_headers['Content-Disposition'] = response.headers['Content-Disposition']

            return Response(
                response.content,
                status=response.status_code,
                headers=response_headers,
                direct_passthrough=True
            )

        # Return JSON response
        return Response(
            response.content,
            status=response.status_code,
            content_type="application/json"
        )

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "API service unavailable"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "API request timeout"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Auth routes
@app.route("/api/auth/captcha", methods=["GET"])
def get_captcha():
    return proxy_request("GET", "/api/auth/captcha")


@app.route("/api/auth/register", methods=["POST"])
def register():
    return proxy_request("POST", "/api/auth/register")


@app.route("/api/auth/login", methods=["POST"])
def login():
    return proxy_request("POST", "/api/auth/login")


# User routes
@app.route("/api/users/me", methods=["GET", "PUT"])
def get_current_user():
    return proxy_request(request.method, "/api/users/me")


@app.route("/api/users/me/password", methods=["PUT"])
def change_password():
    return proxy_request("PUT", "/api/users/me/password")


@app.route("/api/users/me/photo", methods=["PUT", "DELETE"])
def update_profile_photo():
    return proxy_request(request.method, "/api/users/me/photo")


@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    return proxy_request("GET", f"/api/users/{user_id}")


# File routes - SPECIFIC routes MUST come before generic routes!
@app.route("/api/files/upload", methods=["POST"])
def upload_file():
    return proxy_request("POST", "/api/files/upload")


@app.route("/api/files/my-files", methods=["GET"])
def get_my_files():
    return proxy_request("GET", "/api/files/my-files")


@app.route("/api/files/shared-with-me", methods=["GET"])
def get_shared_with_me():
    return proxy_request("GET", "/api/files/shared-with-me")


# IMPORTANT: /image/ and /shared/ and /categories must come BEFORE /<int:file_id>
@app.route("/api/files/image/<path:object_path>", methods=["GET"])
def serve_image(object_path):
    """Proxy image requests to API"""
    return proxy_request("GET", f"/api/files/image/{object_path}")


@app.route("/api/files/shared/<share_token>", methods=["GET"])
def get_shared_file(share_token):
    return proxy_request("GET", f"/api/files/shared/{share_token}")


@app.route("/api/files/shared/<share_token>/download", methods=["GET"])
def download_shared_file(share_token):
    return proxy_request("GET", f"/api/files/shared/{share_token}/download")


@app.route("/api/files/categories", methods=["GET"])
def get_categories():
    return proxy_request("GET", "/api/files/categories")


@app.route("/api/files/notifications", methods=["GET"])
def get_notifications():
    return proxy_request("GET", "/api/files/notifications")


@app.route("/api/files/notifications/mark-read", methods=["POST"])
def mark_notifications_read():
    return proxy_request("POST", "/api/files/notifications/mark-read")


@app.route("/api/files/<int:file_id>/download", methods=["GET"])
def download_file(file_id):
    return proxy_request("GET", f"/api/files/{file_id}/download")


@app.route("/api/files/<int:file_id>/share", methods=["POST"])
def share_file(file_id):
    return proxy_request("POST", f"/api/files/{file_id}/share")


@app.route("/api/files/<int:file_id>", methods=["GET", "PUT", "DELETE"])
def manage_file(file_id):
    return proxy_request(request.method, f"/api/files/{file_id}")


# Search routes
@app.route("/api/search", methods=["GET"])
def search_files():
    return proxy_request("GET", "/api/search")


@app.route("/api/search/public", methods=["GET"])
def search_public_files():
    return proxy_request("GET", "/api/search/public")


@app.route("/api/search/user/<int:user_id>", methods=["GET"])
def search_user_public_files(user_id):
    return proxy_request("GET", f"/api/search/user/{user_id}")


# Admin routes
@app.route("/api/admin/dashboard", methods=["GET"])
def admin_dashboard():
    return proxy_request("GET", "/api/admin/dashboard")


@app.route("/api/admin/users", methods=["GET"])
def list_users():
    return proxy_request("GET", "/api/admin/users")


@app.route("/api/admin/users/<int:user_id>", methods=["GET", "PUT", "DELETE"])
def admin_manage_user(user_id):
    return proxy_request(request.method, f"/api/admin/users/{user_id}")


@app.route("/api/admin/users/<int:user_id>/reset-password", methods=["POST"])
def admin_reset_password(user_id):
    return proxy_request("POST", f"/api/admin/users/{user_id}/reset-password")


@app.route("/api/admin/logs", methods=["GET"])
def get_logs():
    return proxy_request("GET", "/api/admin/logs")


@app.route("/api/admin/files", methods=["GET"])
def admin_list_files():
    return proxy_request("GET", "/api/admin/files")


@app.route("/api/admin/files/<int:file_id>", methods=["DELETE"])
def admin_delete_file(file_id):
    return proxy_request("DELETE", f"/api/admin/files/{file_id}")


# Health check
@app.route("/health", methods=["GET"])
def health():
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type", "application/json")
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=os.getenv("FLASK_ENV") == "development")
