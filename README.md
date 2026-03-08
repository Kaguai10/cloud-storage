<div align="center">
  <img src="https://readme-typing-svg.herokuapp.com?size=30&color=ADD8E6&center=true&vCenter=true&width=650&lines=☁️+Mini+Cloud+Storage">
</div>
<div align="center">
  <img src="https://github.com/Kaguai10/cloud-storage/blob/main/images/cloud-storage.png" width="75%">

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![MinIO](https://img.shields.io/badge/MinIO-Latest-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

</div>

## ✨ Features

<p>A full-stack cloud storage application built with Flask, PostgreSQL, and MinIO. Store, share, and manage your files securely in the cloud.</p>

### 👤 User Features

- **🔐 Authentication & Security**
  - Registration with image-based captcha
  - Secure login with JWT tokens
  - Password strength validation
  - Show/hide password toggle

- **📁 File Management**
  - Upload files via drag & drop, camera, or browse
  - Add metadata: filename, category, visibility
  - Edit file details
  - Delete files
  - Download files with tracking

- **👁️ File Visibility Control**
  - **Public** - Visible and downloadable by everyone
  - **Private** - Only visible to owner
  - **Semi-Public** - Share with specific users

- **🔍 Search & Filter**
  - Search by filename
  - Filter by category (Personal, Work, Family, Travel, Nature, Art, Other)
  - Combined search + category filter

- **📤 File Sharing**
  - Share files with other users
  - Shareable links with tokens
  - View files shared with you
  - Real-time notifications

- **👤 Profile Management**
  - Update username and email
  - Change password
  - Upload/update profile photo (avatar)
  - View account statistics

### 👨‍💼 Admin Features

- **📊 Dashboard** - User and file statistics, recent activity, top users
- **👥 User Management** - Full CRUD operations on users
- **📁 File Management** - View and delete any public file
- **📋 Activity Logs** - Comprehensive logging with filters

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Frontend   │───▶│   Backend   │───▶│     API     │
│  (Flask)    │    │  (Flask)    │    │   (Flask)   │
│  Port 5000  │    │  Port 5001  │    │  Port 8080  │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    ▼                        ▼                        ▼
             ┌────────────┐          ┌────────────┐          ┌────────────┐
             │ PostgreSQL │          │   MinIO    │          │   Logs     │
             │   :5432    │          │   :9000    │          │  Volume    │
             └────────────┘          └────────────┘          └────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Flask + Jinja2 + Bootstrap 5 |
| **Backend** | Flask (API Proxy) |
| **API** | Flask REST API |
| **Database** | PostgreSQL 15 |
| **Object Storage** | MinIO |
| **Authentication** | JWT (PyJWT) |
| **Password Hashing** | bcrypt |
| **ORM** | SQLAlchemy |
| **Captcha** | Custom image-based (PIL) |
| **Containerization** | Docker + Docker Compose |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/kaguai10/cloud-storage.git
cd cloud-storage
```

#### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your settings
```

#### 3. Start All Services

```bash
docker compose up -d
```

#### 4. Access the Application

| Service | PORT | Credentials |
|---------|-----|-------------|
| **Frontend** | 5000 | - |
| **Backend** | 5001 | - |
| **API** | 8080 | - |
| **MinIO Console** | 9001 | `adminminio` / `MinioSecret2026!` |
| **PostgreSQL** | 5432 | `clouduserdb` / `cloudpassdb_secure2026` |
| **Admin Panel** | 5000/admin | `admin` / `admin123` |

> ⚠️ **SECURITY**: Change the default admin password immediately after first login!

### PostgreSQL Connection

**Connect via Docker:**
```bash
docker exec -it cloud-storage-postgres-1 psql -U clouduserdb -d clouddb
```

**Connect from Host:**
```bash
psql -h localhost -p 5432 -U clouduserdb -d clouddb
```

**Connection String:**
```
postgresql://clouduserdb:cloudpassdb_secure2026@localhost:5432/clouddb
```

### Stop Services

```bash
# Stop containers
docker-compose down

# Stop and remove volumes (⚠️ DELETES ALL DATA)
docker-compose down -v
```

## 📂 Project Structure

```
cloud-storage/
├── api/                        # REST API service
│   ├── app.py                 # Main application factory
│   ├── config.py              # Configuration settings
│   ├── models.py              # SQLAlchemy models
│   ├── database.py            # Database connection
│   ├── health.py              # Health check endpoint
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile
│   ├── wait-for-db.sh         # PostgreSQL wait script
│   ├── routes/                # API route handlers
│   │   ├── auth.py            # Authentication
│   │   ├── users.py           # User management
│   │   ├── admin.py           # Admin operations
│   │   ├── files.py           # File CRUD
│   │   └── search.py          # Search functionality
│   ├── services/              # Business logic
│   │   ├── auth_service.py    # JWT, password hashing
│   │   ├── storage.py         # MinIO operations
│   │   └── minio_init.py      # MinIO initialization
│   └── utils/                 # Utilities
│       ├── captcha.py         # Captcha generation
│       ├── validator.py       # Input validation
│       ├── logger.py          # Logging setup
│       └── crypto.py          # Encryption utilities
│
├── backend/                   # Backend proxy service
│   ├── app.py                 # Proxy to API
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                  # Frontend web service
│   ├── app.py                 # Flask web app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── templates/             # Jinja2 templates
│       ├── base.html          # Base template
│       ├── home.html          # Public files
│       ├── login.html         # Login page
│       ├── register.html      # Registration
│       ├── settings.html      # User settings
│       ├── upload.html        # File upload
│       ├── search.html        # Search page
│       ├── my_files.html      # User's files
│       ├── shared_with_me.html # Shared files
│       ├── shared_file.html   # Single shared file
│       ├── file_detail.html   # File details
│       ├── file_edit.html     # Edit file
│       ├── file_share.html    # Share file
│       └── admin/             # Admin templates
│
├── scripts/                   # Utility scripts
│   └── startup-info.sh        # Startup information
│
├── docker-compose.yml         # Docker orchestration
├── .env                       # Environment variables
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # Documentation
```

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/auth/captcha` | Get captcha image |
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | User login |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/me` | Get current user |
| `PUT` | `/api/users/me` | Update profile |
| `PUT` | `/api/users/me/password` | Change password |
| `PUT` | `/api/users/me/photo` | Update profile photo |
| `DELETE` | `/api/users/me/photo` | Delete profile photo |

### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/files/upload` | Upload file |
| `GET` | `/api/files/my-files` | Get user's files |
| `GET` | `/api/files/shared-with-me` | Get shared files |
| `GET` | `/api/files/<id>` | Get file details |
| `PUT` | `/api/files/<id>` | Update file |
| `DELETE` | `/api/files/<id>` | Delete file |
| `GET` | `/api/files/<id>/download` | Download file |
| `POST` | `/api/files/<id>/share` | Share file |
| `GET` | `/api/files/image/<path>` | Serve image |
| `GET` | `/api/files/shared/<token>` | Get shared file |
| `GET` | `/api/files/shared/<token>/download` | Download shared file |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search` | Search files |
| `GET` | `/api/search/public` | Search public files |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/files/notifications` | Get notifications |
| `POST` | `/api/files/notifications/mark-read` | Mark all as read |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/dashboard` | Dashboard statistics |
| `GET` | `/api/admin/users` | List all users |
| `GET` | `/api/admin/users/<id>` | Get user details |
| `PUT` | `/api/admin/users/<id>` | Update user |
| `DELETE` | `/api/admin/users/<id>` | Delete user |
| `POST` | `/api/admin/users/<id>/reset-password` | Reset user password |
| `GET` | `/api/admin/files` | List all public files |
| `DELETE` | `/api/admin/files/<id>` | Delete any file |
| `GET` | `/api/admin/logs` | Activity logs |

## 🔒 Security Best Practices

1. **Change Default Passwords**
   - Admin: `admin` / `admin123`
   - MinIO: Set strong password in `.env`
   - Database: Use strong password

2. **Production Deployment**
   - Use HTTPS
   - Set strong `SECRET_KEY` and `JWT_SECRET`
   - Disable debug mode
   - Use secrets manager for environment variables

3. **Data Protection**
   - Regular backups of PostgreSQL data
   - Backup MinIO storage volumes
   - Keep `.env` file secure (never commit to Git)

4. **File Upload Security**
   - File type validation
   - File size limits (default 5MB)
   - Sanitized filenames

## 📄 License

MIT License.
