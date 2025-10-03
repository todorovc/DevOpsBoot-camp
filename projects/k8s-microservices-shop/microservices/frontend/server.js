const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const axios = require('axios');
const winston = require('winston');
const client = require('prom-client');

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Initialize Prometheus metrics
const register = client.register;
client.collectDefaultMetrics({ register });

// Custom metrics
const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'route', 'status_code']
});

// Configure Winston logger
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console()
  ]
});

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"]
    }
  }
}));

// CORS configuration
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: process.env.RATE_LIMIT || 100,
  message: 'Too many requests from this IP'
});
app.use(limiter);

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    httpRequestDuration
      .labels(req.method, req.route?.path || req.path, res.statusCode)
      .observe(duration / 1000);
    
    logger.info('HTTP Request', {
      method: req.method,
      url: req.url,
      statusCode: res.statusCode,
      duration: `${duration}ms`,
      userAgent: req.get('User-Agent'),
      ip: req.ip
    });
  });
  next();
});

// Service discovery configuration
const SERVICES = {
  USER_SERVICE: process.env.USER_SERVICE_URL || 'http://user-service:8080',
  PRODUCT_SERVICE: process.env.PRODUCT_SERVICE_URL || 'http://product-service:8080',
  ORDER_SERVICE: process.env.ORDER_SERVICE_URL || 'http://order-service:8080',
  PAYMENT_SERVICE: process.env.PAYMENT_SERVICE_URL || 'http://payment-service:8080'
};

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    service: 'frontend-service',
    version: process.env.SERVICE_VERSION || '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Readiness check endpoint
app.get('/ready', async (req, res) => {
  try {
    // Check if dependent services are available
    const checks = await Promise.allSettled([
      axios.get(`${SERVICES.USER_SERVICE}/health`, { timeout: 2000 }),
      axios.get(`${SERVICES.PRODUCT_SERVICE}/health`, { timeout: 2000 }),
      axios.get(`${SERVICES.ORDER_SERVICE}/health`, { timeout: 2000 })
    ]);

    const allHealthy = checks.every(check => 
      check.status === 'fulfilled' && check.value.status === 200
    );

    if (allHealthy) {
      res.status(200).json({ status: 'ready' });
    } else {
      res.status(503).json({ status: 'not ready' });
    }
  } catch (error) {
    logger.error('Readiness check failed', { error: error.message });
    res.status(503).json({ status: 'not ready', error: error.message });
  }
});

// Metrics endpoint
app.get('/metrics', async (req, res) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    res.status(500).end(error);
  }
});

// Main routes
app.get('/', (req, res) => {
  res.json({
    message: 'Welcome to Online Shop',
    service: 'frontend-service',
    version: process.env.SERVICE_VERSION || '1.0.0',
    endpoints: {
      health: '/health',
      ready: '/ready',
      metrics: '/metrics',
      api: {
        products: '/api/products',
        users: '/api/users',
        orders: '/api/orders'
      }
    }
  });
});

// API proxy routes
app.use('/api/users', async (req, res) => {
  try {
    const response = await axios({
      method: req.method,
      url: `${SERVICES.USER_SERVICE}${req.path}`,
      data: req.body,
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': req.ip
      },
      timeout: 10000
    });
    res.status(response.status).json(response.data);
  } catch (error) {
    logger.error('User service error', { error: error.message, path: req.path });
    res.status(error.response?.status || 500).json({
      error: 'User service unavailable'
    });
  }
});

app.use('/api/products', async (req, res) => {
  try {
    const response = await axios({
      method: req.method,
      url: `${SERVICES.PRODUCT_SERVICE}${req.path}`,
      data: req.body,
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': req.ip
      },
      timeout: 10000
    });
    res.status(response.status).json(response.data);
  } catch (error) {
    logger.error('Product service error', { error: error.message, path: req.path });
    res.status(error.response?.status || 500).json({
      error: 'Product service unavailable'
    });
  }
});

app.use('/api/orders', async (req, res) => {
  try {
    const response = await axios({
      method: req.method,
      url: `${SERVICES.ORDER_SERVICE}${req.path}`,
      data: req.body,
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': req.ip
      },
      timeout: 10000
    });
    res.status(response.status).json(response.data);
  } catch (error) {
    logger.error('Order service error', { error: error.message, path: req.path });
    res.status(error.response?.status || 500).json({
      error: 'Order service unavailable'
    });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  logger.error('Unhandled error', { 
    error: error.message, 
    stack: error.stack,
    url: req.url,
    method: req.method
  });
  
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'production' ? 'Something went wrong' : error.message
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not found',
    path: req.path
  });
});

// Graceful shutdown
const server = app.listen(PORT, '0.0.0.0', () => {
  logger.info(`Frontend service started on port ${PORT}`, {
    service: 'frontend-service',
    version: process.env.SERVICE_VERSION || '1.0.0',
    environment: process.env.NODE_ENV || 'development'
  });
});

// Handle shutdown signals
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  server.close(() => {
    logger.info('Process terminated');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  server.close(() => {
    logger.info('Process terminated');
    process.exit(0);
  });
});

module.exports = app;