# 🚀 Quick Start Guide

Deploy the Online Shop microservices to Linode LKE in under 10 minutes!

## Prerequisites ✅

- Linode account with LKE cluster running
- kubectl configured to access your cluster
- Docker installed (for building custom images)

## 1. Setup LKE Cluster (5 minutes)

### Create LKE Cluster on Linode
1. **Login to Linode Cloud Manager**
2. **Create LKE Cluster**:
   - Navigate to "Kubernetes" in the sidebar
   - Click "Create Cluster"
   - Choose region (e.g., Newark, NJ)
   - Select node pool: 3 × Linode 4GB ($36/month each)
   - Cluster name: `online-shop-k8s`
   - Click "Create Cluster"

3. **Download Kubeconfig**:
   - Wait for cluster to be ready (3-5 minutes)
   - Download kubeconfig file
   - Configure kubectl:

```bash
# Set kubeconfig
export KUBECONFIG=~/Downloads/online-shop-k8s-kubeconfig.yaml

# Verify connection
kubectl get nodes
```

## 2. Deploy Application (3 minutes)

### Clone and Deploy
```bash
# Clone repository
git clone <repository-url>
cd k8s-microservices-shop

# Deploy everything with one command
./scripts/deploy.sh deploy production

# Monitor deployment
watch kubectl get pods -n online-shop
```

## 3. Access Your Application (2 minutes)

### Get External IP
```bash
# Wait for external IP assignment
kubectl get ingress -n online-shop

# Get the external IP
EXTERNAL_IP=$(kubectl get ingress online-shop-ingress -n online-shop -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Application URL: http://$EXTERNAL_IP"
```

### Test the Application
```bash
# Test frontend
curl http://$EXTERNAL_IP/

# Test API endpoints
curl http://$EXTERNAL_IP/api/products
curl http://$EXTERNAL_IP/health
```

## 🎉 Success!

Your microservices application is now running on Linode LKE with:

- ✅ **Frontend**: Node.js application
- ✅ **Microservices**: User, Product, Order services  
- ✅ **Redis Cache**: Persistent storage
- ✅ **Load Balancer**: Linode LoadBalancer
- ✅ **Security**: RBAC, Network Policies, Security Contexts
- ✅ **Monitoring**: Health checks and metrics

## Next Steps 📈

### View Application Status
```bash
# Check all resources
kubectl get all -n online-shop

# View logs
kubectl logs -f deployment/frontend -n online-shop

# Monitor resources
kubectl top pods -n online-shop
```

### Scale Your Application
```bash
# Scale frontend
kubectl scale deployment frontend --replicas=5 -n online-shop

# Scale product service
kubectl scale deployment product-service --replicas=3 -n online-shop
```

### Access Services Individually
```bash
# Port forward to specific services
kubectl port-forward service/frontend-service 3000:3000 -n online-shop
kubectl port-forward service/redis-service 6379:6379 -n online-shop
```

## Cleanup 🧹

When you're done testing:

```bash
# Remove all resources
./scripts/deploy.sh cleanup

# Verify cleanup
kubectl get all -n online-shop
```

## Troubleshooting 🔧

### Common Issues

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n online-shop
kubectl logs <pod-name> -n online-shop
```

**No external IP:**
```bash
# Linode LoadBalancer may take 2-3 minutes
kubectl get svc -n ingress-nginx
kubectl get events -n online-shop
```

**Services not communicating:**
```bash
# Test DNS resolution
kubectl exec -it deployment/frontend -n online-shop -- nslookup redis-service
```

## Cost Estimation 💰

**Linode LKE Cluster:**
- 3 × Linode 4GB nodes: ~$108/month
- LoadBalancer: ~$10/month
- Block Storage (Redis): ~$2/month

**Total: ~$120/month** for a production-ready setup

## Advanced Features 🔥

Once deployed, explore these advanced features:

### Security
- RBAC policies active
- Network policies enforced
- Non-root containers
- Secret management

### Monitoring
- Prometheus metrics on `/metrics`
- Health checks on `/health`
- Ready checks on `/ready`

### High Availability
- Multi-replica deployments
- Rolling updates
- Self-healing
- Auto-restart on failures

---

**🎯 That's it!** Your production-ready microservices application is running on Kubernetes with all best practices implemented.