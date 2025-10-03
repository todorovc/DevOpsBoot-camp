# Kubernetes Microservices Online Shop

A production-ready microservices application deployed on Kubernetes with security best practices, monitoring, and observability.

## 🏗️ Architecture Overview

This project demonstrates a complete microservices architecture running on Kubernetes, featuring:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     Ingress     │    │   Frontend      │
│   (Linode LB)   │───▶│   Controller    │───▶│   (Node.js)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 │                                 │
                       ▼                                 ▼                                 ▼
              ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
              │  User Service   │           │ Product Service │           │ Order Service   │
              │     (Go)        │           │    (Python)     │           │   (Node.js)     │
              └─────────────────┘           └─────────────────┘           └─────────────────┘
                       │                             │                             │
                       └─────────────────────────────┼─────────────────────────────┘
                                                     │
                                            ┌─────────────────┐
                                            │  Redis Cache    │
                                            │  (Persistent)   │
                                            └─────────────────┘
```

## 🚀 Technologies Used

### **Microservices Stack**
- **Frontend**: Node.js + Express
- **User Service**: Go + Gorilla Mux
- **Product Service**: Python + Flask
- **Order Service**: Node.js + Express
- **Payment Service**: Node.js + Express

### **Infrastructure & Platform**
- **Kubernetes**: Container orchestration
- **Linode LKE**: Managed Kubernetes service
- **Redis**: Caching and session storage
- **Docker**: Containerization
- **Nginx Ingress**: Load balancing and SSL termination

### **Security & Monitoring**
- **RBAC**: Role-based access control
- **Network Policies**: Micro-segmentation
- **Security Contexts**: Non-root containers
- **Prometheus**: Metrics collection
- **Health Checks**: Liveness, readiness, and startup probes

## 📋 Prerequisites

### Required Tools
- **kubectl** (v1.24+): Kubernetes CLI
- **Docker** (v20.10+): Container runtime
- **Git**: Version control

### Optional Tools
- **Helm** (v3.8+): Package manager for Kubernetes
- **k9s**: Terminal-based Kubernetes dashboard
- **kubectx**: Context and namespace switcher

### Linode Account Setup
1. **Linode Account**: Active account with billing enabled
2. **LKE Cluster**: Kubernetes cluster running v1.24+
3. **kubectl Configuration**: Local access to your cluster

```bash
# Download kubeconfig from Linode Cloud Manager
# and set KUBECONFIG environment variable
export KUBECONFIG=~/Downloads/kubeconfig.yaml

# Verify connection
kubectl cluster-info
```

## 🛠️ Quick Deployment

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd k8s-microservices-shop

# Make deployment script executable
chmod +x scripts/deploy.sh
```

### 2. Deploy to Linode LKE
```bash
# Production deployment
./scripts/deploy.sh deploy production

# Development deployment  
./scripts/deploy.sh deploy development
```

### 3. Access the Application
```bash
# Get ingress IP
kubectl get ingress -n online-shop

# Access application
curl http://<INGRESS_IP>
```

## 📁 Project Structure

```
k8s-microservices-shop/
├── microservices/                  # Application code
│   ├── frontend/                   # Node.js frontend
│   ├── user-service/               # Go user service
│   ├── product-service/            # Python product service
│   ├── order-service/              # Node.js order service
│   └── payment-service/            # Node.js payment service
├── k8s-manifests/                  # Kubernetes configurations
│   ├── base/                       # Base manifests
│   │   ├── namespace.yaml          # Namespace and quotas
│   │   ├── configmap.yaml          # Configuration
│   │   ├── secrets.yaml            # Sensitive data
│   │   ├── frontend-deployment.yaml
│   │   └── ingress.yaml            # Load balancing
│   ├── security/                   # Security policies
│   │   ├── rbac.yaml               # Role-based access
│   │   └── network-policies.yaml   # Network security
│   ├── monitoring/                 # Observability
│   └── overlays/                   # Environment-specific
│       ├── development/
│       ├── staging/
│       └── production/
├── infrastructure/                 # Supporting services
│   ├── redis/                      # Cache deployment
│   └── databases/                  # Database configs
├── scripts/                        # Automation scripts
│   ├── deploy.sh                   # Main deployment script
│   ├── build-images.sh             # Docker build script
│   └── monitoring-setup.sh         # Monitoring setup
└── docs/                          # Documentation
    ├── DEPLOYMENT.md               # Deployment guide
    ├── SECURITY.md                 # Security best practices
    └── TROUBLESHOOTING.md          # Common issues
```

## 🔐 Security Features

### **Production Security Best Practices**

#### **Container Security**
- ✅ Non-root containers (`runAsNonRoot: true`)
- ✅ Read-only root filesystem
- ✅ Dropped capabilities (`drop: [ALL]`)
- ✅ Security contexts enforced
- ✅ Resource limits configured

#### **Network Security**
- ✅ Network policies for micro-segmentation
- ✅ Deny-all default policy
- ✅ Service-to-service communication restrictions
- ✅ Ingress security headers
- ✅ TLS encryption

#### **Access Control**
- ✅ RBAC with minimal permissions
- ✅ Service accounts per service
- ✅ Namespace isolation
- ✅ Secret management
- ✅ Token auto-mounting disabled

#### **Runtime Security**
- ✅ Pod Security Standards
- ✅ Seccomp profiles
- ✅ AppArmor integration
- ✅ Security scanning

## 📊 Monitoring & Observability

### **Health Checks**
Each service implements comprehensive health checks:

```yaml
# Liveness Probe - Restart if unhealthy
livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10

# Readiness Probe - Remove from service if not ready  
readinessProbe:
  httpGet:
    path: /ready
    port: http
  initialDelaySeconds: 10
  periodSeconds: 5

# Startup Probe - Allow slow startup
startupProbe:
  httpGet:
    path: /health
    port: http
  failureThreshold: 10
```

### **Metrics Collection**
- **Prometheus**: Metrics scraping and storage
- **Custom Metrics**: Business metrics per service
- **Infrastructure Metrics**: Resource utilization
- **Alert Rules**: Proactive monitoring

### **Logging**
- **Structured Logging**: JSON format for all services
- **Log Aggregation**: Centralized log collection
- **Log Levels**: Configurable verbosity
- **Request Tracing**: Correlation IDs

## 🌐 Service Communication

### **Internal Communication**
Services communicate via Kubernetes Services using DNS:

```yaml
# Service Discovery
USER_SERVICE_URL: "http://user-service:8080"
PRODUCT_SERVICE_URL: "http://product-service:8080"
ORDER_SERVICE_URL: "http://order-service:8080"
```

### **External Access**
External traffic flows through the Ingress Controller:

```
Internet → Linode LoadBalancer → Ingress Controller → Services → Pods
```

### **API Gateway Pattern**
The frontend service acts as an API gateway, routing requests to appropriate microservices.

## 🚦 Deployment Environments

### **Development**
```bash
./scripts/deploy.sh deploy development
```
- Relaxed security policies
- Debug logging enabled
- Single replica deployments
- In-memory caching

### **Staging**
```bash
./scripts/deploy.sh deploy staging  
```
- Production-like configuration
- Load testing enabled
- Multi-replica deployments
- Persistent storage

### **Production**
```bash
./scripts/deploy.sh deploy production
```
- Full security enforcement
- High availability setup
- Auto-scaling enabled
- Monitoring and alerting

## 🔧 Operations

### **Scaling**
```bash
# Scale individual services
kubectl scale deployment frontend --replicas=5 -n online-shop
kubectl scale deployment product-service --replicas=3 -n online-shop

# Auto-scaling (if HPA configured)
kubectl autoscale deployment frontend --cpu-percent=70 --min=2 --max=10 -n online-shop
```

### **Updates**
```bash
# Rolling update
kubectl set image deployment/frontend frontend=myregistry/frontend:v2.0.0 -n online-shop

# Check rollout status
kubectl rollout status deployment/frontend -n online-shop

# Rollback if needed
kubectl rollout undo deployment/frontend -n online-shop
```

### **Debugging**
```bash
# View logs
kubectl logs -f deployment/frontend -n online-shop

# Execute into pod
kubectl exec -it deployment/frontend -n online-shop -- /bin/sh

# Port forward for direct access
kubectl port-forward service/frontend-service 3000:3000 -n online-shop
```

### **Monitoring**
```bash
# View resource usage
kubectl top pods -n online-shop
kubectl top nodes

# Check service endpoints
kubectl get endpoints -n online-shop

# View events
kubectl get events -n online-shop --sort-by='.lastTimestamp'
```

## 🧪 Testing

### **Health Check Testing**
```bash
# Test all health endpoints
kubectl get pods -n online-shop -o wide
for pod in $(kubectl get pods -n online-shop -o name); do
  kubectl exec $pod -n online-shop -- curl -f localhost:8080/health || echo "Health check failed for $pod"
done
```

### **Load Testing**
```bash
# Install hey (HTTP load testing tool)
# Test frontend
hey -n 1000 -c 10 http://<INGRESS_IP>/

# Test API endpoints
hey -n 500 -c 5 http://<INGRESS_IP>/api/products
```

### **Integration Testing**
```bash
# Run integration tests
./scripts/integration-tests.sh
```

## 📚 Best Practices Implemented

### **Kubernetes Best Practices**
- ✅ Resource requests and limits
- ✅ Proper labeling and annotations  
- ✅ Health checks for all containers
- ✅ Graceful shutdown handling
- ✅ Configuration externalization
- ✅ Secret management
- ✅ Service mesh ready

### **Microservices Best Practices**
- ✅ Single responsibility per service
- ✅ Database per service
- ✅ API versioning
- ✅ Circuit breaker patterns
- ✅ Retry mechanisms
- ✅ Timeout configurations
- ✅ Bulkhead isolation

### **Security Best Practices**
- ✅ Principle of least privilege
- ✅ Defense in depth
- ✅ Zero trust networking
- ✅ Regular security updates
- ✅ Vulnerability scanning
- ✅ Audit logging

## 🔍 Troubleshooting

### **Common Issues**

#### **Pods Not Starting**
```bash
# Check pod status
kubectl get pods -n online-shop

# View pod events
kubectl describe pod <pod-name> -n online-shop

# Check logs
kubectl logs <pod-name> -n online-shop
```

#### **Service Communication Issues**
```bash
# Test DNS resolution
kubectl exec -it <pod-name> -n online-shop -- nslookup user-service

# Test service connectivity  
kubectl exec -it <pod-name> -n online-shop -- curl http://user-service:8080/health
```

#### **Ingress Issues**
```bash
# Check ingress status
kubectl get ingress -n online-shop
kubectl describe ingress online-shop-ingress -n online-shop

# Check ingress controller logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

### **Performance Issues**
```bash
# Check resource utilization
kubectl top pods -n online-shop

# Check for resource constraints
kubectl describe pod <pod-name> -n online-shop | grep -i "resource\|limit\|request"

# Monitor events for throttling
kubectl get events -n online-shop | grep -i "resource\|memory\|cpu"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Kubernetes Community**: For excellent documentation and tools
- **Linode**: For providing managed Kubernetes service
- **Cloud Native Computing Foundation**: For promoting cloud native technologies

---

**⚡ Production Ready**: This project implements industry best practices for security, reliability, and observability in Kubernetes environments.