# Healthcare System - Quick Start Guide

## Overview
This guide will help you deploy the Healthcare System on your Kubernetes cluster in under 10 minutes.

## Prerequisites
- Kubernetes cluster (1.24+) with at least:
  - 50 CPU cores
  - 150GB RAM
  - 1TB storage
- kubectl installed and configured
- Helm 3.8+ installed
- Optional: GPU nodes for AI features

## Quick Installation (Development)

### Option 1: Using the Installation Script

```bash
# Clone or download the chart
cd healthcare-k8s-helm

# Run the installation script
./install.sh

# Follow the prompts:
# - Select environment: 1 (Development)
# - Enter domain: localhost or your-domain.com
# - Wait for installation to complete
```

The script will:
- Add required Helm repositories
- Generate secure passwords
- Deploy the healthcare system
- Save credentials to a file
- Display next steps

### Option 2: Manual Installation

```bash
# Add Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install with minimal configuration
helm install healthcare ./healthcare-k8s-helm \
  --namespace healthcare-dev \
  --create-namespace \
  --set global.domain=localhost \
  --set global.environment=development \
  --set ingress.tls.enabled=false \
  --set aiAgents.llm.gpu.enabled=false \
  --set application.django.replicaCount=2
```

## Verify Installation

```bash
# Check pods are running
kubectl get pods -n healthcare-dev

# Wait for all pods to be ready (this may take 5-10 minutes)
kubectl get pods -n healthcare-dev -w

# Check services
kubectl get svc -n healthcare-dev

# View installation notes
helm get notes healthcare -n healthcare-dev
```

## Access the Application

### Development (Port Forward)
```bash
# Access Django application
kubectl port-forward -n healthcare-dev svc/healthcare-django 8000:8000
# Open: http://localhost:8000

# Access Grafana (if enabled)
kubectl port-forward -n healthcare-dev svc/healthcare-grafana 3000:3000
# Open: http://localhost:3000
```

### Production (with Ingress)
```bash
# Make sure your domain DNS points to your cluster's ingress
# Access via: https://your-domain.com
```

## Common Commands

### View Logs
```bash
# All pods
kubectl logs -n healthcare-dev -l app.kubernetes.io/name=healthcare --tail=100

# Specific component
kubectl logs -n healthcare-dev -l app.kubernetes.io/component=django --tail=50

# Follow logs
kubectl logs -n healthcare-dev -l app.kubernetes.io/component=celery-worker -f
```

### Scale Components
```bash
# Scale Django pods
kubectl scale deployment healthcare-django -n healthcare-dev --replicas=5

# Scale Celery workers
kubectl scale deployment healthcare-celery-worker -n healthcare-dev --replicas=10
```

### Database Access
```bash
# PostgreSQL
kubectl exec -it healthcare-postgresql-0 -n healthcare-dev -- psql -U healthcare

# Redis
kubectl exec -it healthcare-redis-master-0 -n healthcare-dev -- redis-cli
```

## Upgrade Installation

```bash
# Upgrade with new values
helm upgrade healthcare ./healthcare-k8s-helm \
  --namespace healthcare-dev \
  --reuse-values \
  --set application.django.replicaCount=5
```

## Uninstall

```bash
# Uninstall release (keeps data)
helm uninstall healthcare -n healthcare-dev

# Delete namespace and all data
kubectl delete namespace healthcare-dev
```

## Production Deployment

For production deployment:

1. **Review production-values.yaml**
   ```bash
   cp production-values.yaml my-production-values.yaml
   # Edit my-production-values.yaml with your settings
   ```

2. **Set required secrets**
   ```bash
   # Create a secrets file
   cat > secrets.yaml << EOF
   data:
     postgresql:
       auth:
         password: YOUR_SECURE_PASSWORD
     neo4j:
       auth:
         password: YOUR_SECURE_PASSWORD
   application:
     django:
       secrets:
         secretKey: YOUR_DJANGO_SECRET
   EOF
   ```

3. **Deploy to production**
   ```bash
   helm install healthcare ./healthcare-k8s-helm \
     --namespace healthcare-prod \
     --create-namespace \
     --values production-values.yaml \
     --values secrets.yaml
   ```

4. **Enable monitoring and logging**
   - Access Grafana: https://monitoring.your-domain.com
   - Access Kibana: https://logs.your-domain.com

## Troubleshooting

### Pods Not Starting
```bash
# Describe the pod to see errors
kubectl describe pod <pod-name> -n healthcare-dev

# Check events
kubectl get events -n healthcare-dev --sort-by='.lastTimestamp'
```

### Out of Resources
```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -n healthcare-dev
```

### Persistent Volume Issues
```bash
# Check PVCs
kubectl get pvc -n healthcare-dev

# Describe PVC
kubectl describe pvc <pvc-name> -n healthcare-dev
```

### Database Connection Issues
```bash
# Check database service
kubectl get svc healthcare-postgresql -n healthcare-dev

# Test connection
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql -h healthcare-postgresql.healthcare-dev.svc.cluster.local -U healthcare
```

## Next Steps

1. **Configure your application**
   - Update Django settings in ConfigMap
   - Set up initial data
   - Configure email/SMS providers

2. **Set up monitoring**
   - Import Grafana dashboards
   - Configure Prometheus alerts
   - Set up log aggregation

3. **Security hardening**
   - Enable network policies
   - Configure RBAC
   - Set up backup strategy
   - Rotate default passwords

4. **Performance tuning**
   - Adjust resource limits
   - Configure autoscaling
   - Optimize database queries

## Getting Help

- Check the full README.md for detailed documentation
- Review values.yaml for all configuration options
- Check logs: `kubectl logs -n healthcare-dev <pod-name>`
- Contact: support@healthcare.example.com

## Architecture Components

The deployment includes:

- **Frontend**: Django web application
- **Background Tasks**: Celery workers and beat scheduler  
- **AI Services**: LLM, RAG, and 25+ specialized agents
- **Databases**: PostgreSQL, Neo4j, Redis
- **Message Queue**: RabbitMQ
- **Object Storage**: MinIO
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack
- **Ingress**: NGINX + Cert-Manager

---

**Ready to deploy?** Run `./install.sh` and follow the prompts!
