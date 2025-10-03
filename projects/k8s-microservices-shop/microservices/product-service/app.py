#!/usr/bin/env python3

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.exceptions import BadRequest, NotFound

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

@dataclass
class Product:
    id: int
    name: str
    description: str
    price: float
    category: str
    stock: int
    image_url: str = ""
    created_at: str = ""
    updated_at: str = ""

class ProductService:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Configuration
        self.redis_client = None
        self.db_connection = None
        self.setup_database()
        self.setup_redis()
        self.setup_routes()
        self.initialize_sample_data()

    def setup_database(self):
        """Setup PostgreSQL connection"""
        try:
            db_config = {
                'host': os.getenv('DB_HOST', 'postgres'),
                'port': int(os.getenv('DB_PORT', '5432')),
                'database': os.getenv('DB_NAME', 'products'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'password')
            }
            
            self.db_connection = psycopg2.connect(**db_config)
            self.create_tables()
            logger.info("Database connection established")
            
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
            # Fallback to in-memory storage
            self.products = {}
            self.next_id = 1

    def setup_redis(self):
        """Setup Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                password=os.getenv('REDIS_PASSWORD', ''),
                decode_responses=True,
                socket_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None

    def create_tables(self):
        """Create database tables if they don't exist"""
        if not self.db_connection:
            return
            
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            category VARCHAR(100) NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            image_url VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
        """
        
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute(create_table_sql)
                self.db_connection.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            self.db_connection.rollback()

    def initialize_sample_data(self):
        """Initialize with sample products"""
        sample_products = [
            Product(1, "Laptop", "High-performance laptop", 999.99, "electronics", 10, 
                   "https://example.com/laptop.jpg"),
            Product(2, "Coffee Mug", "Ceramic coffee mug", 12.99, "home", 50,
                   "https://example.com/mug.jpg"),
            Product(3, "Running Shoes", "Comfortable running shoes", 79.99, "sports", 25,
                   "https://example.com/shoes.jpg"),
            Product(4, "Smartphone", "Latest smartphone model", 699.99, "electronics", 15,
                   "https://example.com/phone.jpg"),
        ]

        for product in sample_products:
            self.create_product(product.__dict__)

    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.before_request
        def before_request():
            g.start_time = time.time()

        @self.app.after_request
        def after_request(response):
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                REQUEST_DURATION.labels(
                    method=request.method,
                    endpoint=request.endpoint or 'unknown'
                ).observe(duration)
                
                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=request.endpoint or 'unknown',
                    status=response.status_code
                ).inc()

            return response

        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'service': 'product-service',
                'version': os.getenv('SERVICE_VERSION', '1.0.0'),
                'timestamp': datetime.utcnow().isoformat(),
                'uptime': time.time() - self.start_time
            })

        @self.app.route('/ready', methods=['GET'])
        def ready():
            checks = {
                'database': self.check_database(),
                'redis': self.check_redis()
            }
            
            all_healthy = all(checks.values())
            status_code = 200 if all_healthy else 503
            
            return jsonify({
                'status': 'ready' if all_healthy else 'not ready',
                'checks': checks
            }), status_code

        @self.app.route('/metrics', methods=['GET'])
        def metrics():
            return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

        @self.app.route('/products', methods=['GET'])
        def get_products():
            try:
                category = request.args.get('category')
                page = int(request.args.get('page', 1))
                limit = int(request.args.get('limit', 10))
                
                products = self.get_products_list(category, page, limit)
                return jsonify(products)
                
            except Exception as e:
                logger.error(f"Error fetching products: {e}")
                return jsonify({'error': 'Failed to fetch products'}), 500

        @self.app.route('/products/<int:product_id>', methods=['GET'])
        def get_product(product_id):
            try:
                product = self.get_product_by_id(product_id)
                if not product:
                    return jsonify({'error': 'Product not found'}), 404
                    
                return jsonify(product)
                
            except Exception as e:
                logger.error(f"Error fetching product {product_id}: {e}")
                return jsonify({'error': 'Failed to fetch product'}), 500

        @self.app.route('/products', methods=['POST'])
        def create_product():
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                product = self.create_product(data)
                return jsonify(product), 201
                
            except Exception as e:
                logger.error(f"Error creating product: {e}")
                return jsonify({'error': 'Failed to create product'}), 500

        @self.app.route('/products/<int:product_id>/stock', methods=['PUT'])
        def update_stock(product_id):
            try:
                data = request.get_json()
                new_stock = data.get('stock')
                
                if new_stock is None:
                    return jsonify({'error': 'Stock value required'}), 400
                
                success = self.update_product_stock(product_id, new_stock)
                if not success:
                    return jsonify({'error': 'Product not found'}), 404
                
                return jsonify({'message': 'Stock updated successfully'})
                
            except Exception as e:
                logger.error(f"Error updating stock: {e}")
                return jsonify({'error': 'Failed to update stock'}), 500

    def check_database(self) -> bool:
        """Check database connectivity"""
        if not self.db_connection:
            return False
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return True
        except:
            return False

    def check_redis(self) -> bool:
        """Check Redis connectivity"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False

    def get_products_list(self, category: Optional[str] = None, page: int = 1, limit: int = 10) -> List[Dict]:
        """Get list of products with optional filtering and pagination"""
        offset = (page - 1) * limit
        
        if self.db_connection:
            try:
                with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    if category:
                        cursor.execute(
                            "SELECT * FROM products WHERE category = %s LIMIT %s OFFSET %s",
                            (category, limit, offset)
                        )
                    else:
                        cursor.execute(
                            "SELECT * FROM products LIMIT %s OFFSET %s",
                            (limit, offset)
                        )
                    
                    products = [dict(row) for row in cursor.fetchall()]
                    
                    # Cache in Redis if available
                    if self.redis_client:
                        cache_key = f"products:{category or 'all'}:{page}:{limit}"
                        self.redis_client.setex(cache_key, 300, json.dumps(products, default=str))
                    
                    return products
            except Exception as e:
                logger.error(f"Database query failed: {e}")
        
        # Fallback to in-memory storage
        products = list(self.products.values()) if hasattr(self, 'products') else []
        if category:
            products = [p for p in products if p.get('category') == category]
        
        return products[offset:offset + limit]

    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Get product by ID"""
        # Check cache first
        if self.redis_client:
            try:
                cached = self.redis_client.get(f"product:{product_id}")
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        if self.db_connection:
            try:
                with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        product = dict(result)
                        # Cache the result
                        if self.redis_client:
                            self.redis_client.setex(f"product:{product_id}", 600, json.dumps(product, default=str))
                        return product
            except Exception as e:
                logger.error(f"Database query failed: {e}")

        # Fallback
        return self.products.get(product_id) if hasattr(self, 'products') else None

    def create_product(self, data: Dict) -> Dict:
        """Create a new product"""
        if self.db_connection:
            try:
                with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        INSERT INTO products (name, description, price, category, stock, image_url)
                        VALUES (%(name)s, %(description)s, %(price)s, %(category)s, %(stock)s, %(image_url)s)
                        RETURNING *
                    """, data)
                    
                    product = dict(cursor.fetchone())
                    self.db_connection.commit()
                    
                    # Invalidate cache
                    if self.redis_client:
                        self.redis_client.delete(f"products:*")
                    
                    return product
            except Exception as e:
                logger.error(f"Failed to create product: {e}")
                self.db_connection.rollback()
                raise

        # Fallback
        if not hasattr(self, 'products'):
            self.products = {}
            self.next_id = 1
            
        data['id'] = self.next_id
        data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = datetime.utcnow().isoformat()
        self.products[self.next_id] = data
        self.next_id += 1
        return data

    def update_product_stock(self, product_id: int, new_stock: int) -> bool:
        """Update product stock"""
        if self.db_connection:
            try:
                with self.db_connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE products SET stock = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (new_stock, product_id)
                    )
                    
                    success = cursor.rowcount > 0
                    self.db_connection.commit()
                    
                    if success and self.redis_client:
                        # Invalidate cache
                        self.redis_client.delete(f"product:{product_id}")
                        self.redis_client.delete(f"products:*")
                    
                    return success
            except Exception as e:
                logger.error(f"Failed to update stock: {e}")
                self.db_connection.rollback()
                return False

        # Fallback
        if hasattr(self, 'products') and product_id in self.products:
            self.products[product_id]['stock'] = new_stock
            self.products[product_id]['updated_at'] = datetime.utcnow().isoformat()
            return True
        
        return False

    def run(self):
        """Run the Flask application"""
        self.start_time = time.time()
        port = int(os.getenv('PORT', 8080))
        
        logger.info(f"Starting Product Service on port {port}")
        self.app.run(
            host='0.0.0.0',
            port=port,
            debug=os.getenv('DEBUG', 'false').lower() == 'true'
        )

if __name__ == '__main__':
    service = ProductService()
    service.run()