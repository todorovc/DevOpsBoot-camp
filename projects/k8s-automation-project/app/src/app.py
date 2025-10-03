#!/usr/bin/env python3

import os
import socket
from datetime import datetime
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Demo K8s Application</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f0f0f0; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .header { color: #2c3e50; text-align: center; margin-bottom: 30px; }
        .info-box { background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .status { color: #27ae60; font-weight: bold; }
        .endpoint { background: #3498db; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Demo Kubernetes Application</h1>
            <p class="status">Status: Running</p>
        </div>
        
        <div class="info-box">
            <h3>Application Info:</h3>
            <p><strong>Pod Name:</strong> {{ pod_name }}</p>
            <p><strong>Node Name:</strong> {{ node_name }}</p>
            <p><strong>Namespace:</strong> {{ namespace }}</p>
            <p><strong>Current Time:</strong> {{ current_time }}</p>
        </div>
        
        <div class="info-box">
            <h3>Available Endpoints:</h3>
            <div class="endpoint">GET / - This page</div>
            <div class="endpoint">GET /health - Health check</div>
            <div class="endpoint">GET /api/info - JSON info</div>
            <div class="endpoint">GET /api/version - Application version</div>
        </div>
        
        <div class="info-box">
            <h3>Environment:</h3>
            <p><strong>App Version:</strong> {{ app_version }}</p>
            <p><strong>Environment:</strong> {{ environment }}</p>
            <p><strong>Python Version:</strong> {{ python_version }}</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    """Main page showing application info"""
    pod_name = os.environ.get('HOSTNAME', 'unknown')
    node_name = os.environ.get('NODE_NAME', 'unknown')
    namespace = os.environ.get('POD_NAMESPACE', 'unknown')
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    app_version = os.environ.get('APP_VERSION', '1.0.0')
    environment = os.environ.get('ENVIRONMENT', 'development')
    python_version = os.environ.get('PYTHON_VERSION', 'unknown')
    
    return render_template_string(HTML_TEMPLATE,
                                pod_name=pod_name,
                                node_name=node_name,
                                namespace=namespace,
                                current_time=current_time,
                                app_version=app_version,
                                environment=environment,
                                python_version=python_version)

@app.route('/health')
def health_check():
    """Health check endpoint for Kubernetes probes"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'pod': os.environ.get('HOSTNAME', 'unknown'),
        'version': os.environ.get('APP_VERSION', '1.0.0')
    }), 200

@app.route('/api/info')
def get_info():
    """API endpoint returning detailed application info"""
    return jsonify({
        'application': 'demo-k8s-app',
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'environment': os.environ.get('ENVIRONMENT', 'development'),
        'pod_info': {
            'name': os.environ.get('HOSTNAME', 'unknown'),
            'namespace': os.environ.get('POD_NAMESPACE', 'unknown'),
            'node': os.environ.get('NODE_NAME', 'unknown'),
            'ip': socket.gethostbyname(socket.gethostname())
        },
        'timestamps': {
            'current': datetime.now().isoformat(),
            'started': os.environ.get('STARTED_AT', 'unknown')
        },
        'system': {
            'python_version': os.environ.get('PYTHON_VERSION', 'unknown'),
            'hostname': socket.gethostname()
        }
    })

@app.route('/api/version')
def get_version():
    """Simple version endpoint"""
    return jsonify({
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'build': os.environ.get('BUILD_NUMBER', 'unknown'),
        'commit': os.environ.get('GIT_COMMIT', 'unknown')
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Set startup timestamp
    os.environ['STARTED_AT'] = datetime.now().isoformat()
    
    # Get port from environment or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    print(f"Starting Demo K8s Application on port {port}")
    print(f"Version: {os.environ.get('APP_VERSION', '1.0.0')}")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=False)