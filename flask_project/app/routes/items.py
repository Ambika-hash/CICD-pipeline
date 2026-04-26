from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, limiter
from app.models import Item, User

items_bp = Blueprint('items', __name__)


@items_bp.route('/items', methods=['GET'])
@jwt_required()
def get_items():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    category = request.args.get('category')
    search = request.args.get('search')

    query = Item.query.filter_by(user_id=int(get_jwt_identity()))

    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Item.name.ilike(f'%{search}%'))

    pagination = query.order_by(Item.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page,
        'per_page': per_page,
    }), 200


@items_bp.route('/items/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    item = Item.query.filter_by(id=item_id, user_id=int(get_jwt_identity())).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    return jsonify(item.to_dict()), 200


@items_bp.route('/items', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def create_item():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Item name is required'}), 400

    item = Item(
        name=data['name'],
        description=data.get('description'),
        category=data.get('category'),
        user_id=int(get_jwt_identity()),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'message': 'Item created', 'item': item.to_dict()}), 201


@items_bp.route('/items/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    item = Item.query.filter_by(id=item_id, user_id=int(get_jwt_identity())).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    data = request.get_json()
    if 'name' in data:
        item.name = data['name']
    if 'description' in data:
        item.description = data['description']
    if 'category' in data:
        item.category = data['category']

    db.session.commit()
    return jsonify({'message': 'Item updated', 'item': item.to_dict()}), 200


@items_bp.route('/items/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    item = Item.query.filter_by(id=item_id, user_id=int(get_jwt_identity())).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item deleted'}), 200
