from flask import Blueprint, request, jsonify
from database import db
from models import File, User, SharedFile
from services.auth_service import token_required
from sqlalchemy import or_

search_bp = Blueprint("search", __name__)


@search_bp.route("", methods=["GET"])
@token_required
def search_files():
    """Search for files"""
    current_user = request.current_user
    
    query_param = request.args.get("q", "")
    category = request.args.get("category", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    # Base query - user's own files
    base_query = File.query.filter_by(owner_id=current_user["user_id"])
    
    # Add public files
    public_query = File.query.filter_by(visibility="public")
    
    # Add semipublic files shared with user
    shared_file_ids = db.session.query(File.id).join(
        SharedFile, SharedFile.file_id == File.id
    ).filter(SharedFile.shared_with_user_id == current_user["user_id"]).subquery()

    shared_query = File.query.filter(File.id.in_(shared_file_ids))
    
    # Combine queries
    combined_query = base_query.union(public_query).union(shared_query)
    
    # Apply search filter
    if query_param:
        combined_query = combined_query.filter(
            or_(
                File.filename.ilike(f"%{query_param}%"),
                File.original_filename.ilike(f"%{query_param}%"),
                File.category.ilike(f"%{query_param}%")
            )
        )
    
    # Apply category filter
    if category:
        combined_query = combined_query.filter_by(category=category)
    
    # Order by created_at desc
    combined_query = combined_query.order_by(File.created_at.desc())
    
    # Paginate
    pagination = combined_query.paginate(page=page, per_page=per_page, error_out=False)
    files = pagination.items
    
    return jsonify({
        "files": [f.to_dict() for f in files],
        "query": query_param,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    })


@search_bp.route("/public", methods=["GET"])
def search_public_files():
    """Search public files (no auth required)"""
    query_param = request.args.get("q", "")
    category = request.args.get("category", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Base query - public files only
    query = File.query.filter_by(visibility="public").join(User, File.owner_id == User.id)

    # Apply search filter
    if query_param:
        query = query.filter(
            or_(
                File.filename.ilike(f"%{query_param}%"),
                File.original_filename.ilike(f"%{query_param}%"),
                File.category.ilike(f"%{query_param}%")
            )
        )

    # Apply category filter - use filter() instead of filter_by() after join
    if category:
        query = query.filter(File.category == category)

    # Order by created_at desc
    query = query.order_by(File.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    files = pagination.items

    return jsonify({
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "original_filename": f.original_filename,
                "category": f.category,
                "file_size": f.file_size,
                "mime_type": f.mime_type,
                "visibility": f.visibility,
                "download_count": f.download_count,
                "object_path": f.object_path,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "updated_at": f.updated_at.isoformat() if f.updated_at else None,
                "owner": {
                    "id": f.owner.id,
                    "username": f.owner.username
                } if f.owner else None
            }
            for f in files
        ],
        "query": query_param,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    })


@search_bp.route("/user/<int:user_id>", methods=["GET"])
def search_user_public_files(user_id):
    """Search public files by specific user"""
    query_param = request.args.get("q", "")
    category = request.args.get("category", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    # Base query - public files by user
    query = File.query.filter_by(owner_id=user_id, visibility="public")
    
    # Apply search filter
    if query_param:
        query = query.filter(
            or_(
                File.filename.ilike(f"%{query_param}%"),
                File.original_filename.ilike(f"%{query_param}%"),
                File.category.ilike(f"%{query_param}%")
            )
        )
    
    # Apply category filter
    if category:
        query = query.filter_by(category=category)
    
    # Order by created_at desc
    query = query.order_by(File.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    files = pagination.items
    
    return jsonify({
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "original_filename": f.original_filename,
                "category": f.category,
                "file_size": f.file_size,
                "mime_type": f.mime_type,
                "visibility": f.visibility,
                "download_count": f.download_count,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in files
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    })
