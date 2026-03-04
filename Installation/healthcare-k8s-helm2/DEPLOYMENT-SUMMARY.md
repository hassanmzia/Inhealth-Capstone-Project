# Healthcare System Kubernetes Helm Charts - Deployment Package

## 📦 Package Contents

This complete Helm chart package contains everything needed to deploy your Healthcare System on Kubernetes.

## 🗂️ What's Included

### Core Files
- **Chart.yaml** - Helm chart metadata and dependencies
- **values.yaml** - Default configuration (150+ parameters)
- **production-values.yaml** - Production-ready configuration example

### Templates (20+ Kubernetes Resources)

#### Application Layer
- `django-deployment.yaml` - Django web application with HPA
- `django-configmap.yaml` - Django configuration
- `celery-deployment.yaml` - Celery workers, beat, and flower

#### AI Agents (25+ Microservices)
- `llm-service.yaml` - Large Language Model service with GPU support
- `medical-agents.yaml` - 8 medical agents (diagnostic, treatment, imaging, etc.)
- `administrative-agents.yaml` - 6 admin agents (scheduling, billing, EHR, etc.)
- `communication-agents.yaml` - 5 communication agents (email, SMS, chat, etc.)
- `analytics-agents.yaml` - 5 analytics agents (predictive, reporting, etc.)
- `security-agents.yaml` - 3 security agents (auth, authz, encryption)

#### Data Layer
- `neo4j-statefulset.yaml` - Neo4j graph database cluster

#### Infrastructure
- `namespace.yaml` - Kubernetes namespace
- `rbac.yaml` - Role-Based Access Control
- `secrets.yaml` - Secure credentials management
- `ingress.yaml` - NGINX ingress with TLS/SSL

#### Helpers
- `_helpers.tpl` - Reusable template functions
- `NOTES.txt` - Post-installation instructions

### Documentation
- **README.md** - Comprehensive 300+ line guide
- **QUICKSTART.md** - Get started in 10 minutes
- **install.sh** - Automated installation script

## 🚀 Quick Start

### Extract the Package
```bash
tar -xzf healthcare-k8s-helm.tar.gz
cd healthcare-k8s-helm
```

### Deploy (Automated)
```bash
chmod +x install.sh
./install.sh
```

### Deploy (Manual)
```bash
helm install healthcare . \
  --namespace healthcare-system \
  --create-namespace
```

## 📊 Architecture Summary

### Component Breakdown

| Layer | Components | Pods | CPU | Memory |
|-------|-----------|------|-----|--------|
| **Ingress** | NGINX, Cert-Manager, WAF, Kong, External-DNS | 10-15 | 3-5 cores | 4-8 GB |
| **Application** | Django, Celery, WebSocket, Static Files | 20-50 | 20-80 cores | 40-160 GB |
| **AI Agents** | LLM, RAG, 25+ Microservices | 50-100 | 50-150 cores | 100-300 GB |
| **Data** | PostgreSQL, Neo4j, Redis, RabbitMQ, MinIO | 15-20 | 20-40 cores | 80-160 GB |
| **Monitoring** | Prometheus, Grafana, Alertmanager | 3-5 | 3-8 cores | 12-24 GB |
| **Logging** | Elasticsearch, Logstash, Kibana, Filebeat | 10-15 | 10-20 cores | 40-80 GB |
| **Total** | All Components | **150-200** | **100-200** | **300-400 GB** |

### Resource Requirements

**Development Environment:**
- Nodes: 3-5 nodes
- CPU: 50+ cores
- Memory: 150GB RAM
- Storage: 1TB
- GPU: Optional

**Production Environment:**
- Nodes: 10-20 nodes
- CPU: 200+ cores
- Memory: 400GB RAM
- Storage: 5TB
- GPU: 2-4x NVIDIA A100

## 🔧 Configuration Options

### Key Configuration Parameters

```yaml
# Domain Configuration
global.domain: "healthcare.example.com"

# Application Scaling
application.django.replicaCount: 5
application.django.autoscaling.maxReplicas: 20

# AI Agents
aiAgents.llm.enabled: true
aiAgents.llm.gpu.enabled: true

# Data Persistence
data.postgresql.persistence.size: "500Gi"
data.neo4j.persistence.size: "300Gi"

# Monitoring
monitoring.prometheus.enabled: true
monitoring.grafana.enabled: true

# Logging
logging.elasticsearch.enabled: true
```

### Environment-Specific Deployments

**Development:**
```bash
helm install healthcare . \
  --set global.environment=development \
  --set ingress.tls.enabled=false \
  --set aiAgents.llm.gpu.enabled=false
```

**Staging:**
```bash
helm install healthcare . \
  --set global.environment=staging \
  --set application.django.replicaCount=3
```

**Production:**
```bash
helm install healthcare . \
  --values production-values.yaml \
  --set data.postgresql.auth.password=$POSTGRES_PWD
```

## 🔐 Security Features

### Implemented Security
✅ RBAC (Role-Based Access Control)
✅ Network Policies
✅ Pod Security Policies
✅ Secrets Management
✅ TLS/SSL for Ingress
✅ Certificate Management (cert-manager)
✅ WAF (Web Application Firewall)
✅ Security Context for Pods

### Security Best Practices
1. Change all default passwords
2. Enable TLS for production
3. Configure network policies
4. Use external secrets management
5. Regular security audits
6. Enable pod security standards
7. Implement RBAC policies

## 📈 Monitoring & Observability

### Included Monitoring Stack
- **Prometheus** - Metrics collection
- **Grafana** - Visualization dashboards
- **Alertmanager** - Alert routing
- **Node Exporter** - Node metrics
- **Kube State Metrics** - Cluster metrics

### Access Monitoring
```bash
# Grafana
kubectl port-forward svc/healthcare-grafana 3000:3000 -n healthcare-system

# Prometheus
kubectl port-forward svc/healthcare-prometheus-server 9090:9090 -n healthcare-system
```

## 📝 Logging Stack

### Included Components
- **Elasticsearch** - Log storage and indexing
- **Logstash** - Log processing
- **Kibana** - Log visualization
- **Filebeat** - Log shipping

### Access Logs
```bash
# Kibana
kubectl port-forward svc/healthcare-kibana 5601:5601 -n healthcare-system
```

## 🔄 Upgrade & Rollback

### Upgrade
```bash
helm upgrade healthcare . \
  --namespace healthcare-system \
  --reuse-values \
  --set application.django.image.tag=1.1.0
```

### Rollback
```bash
# List revisions
helm history healthcare -n healthcare-system

# Rollback to previous version
helm rollback healthcare -n healthcare-system

# Rollback to specific revision
helm rollback healthcare 2 -n healthcare-system
```

## 💾 Backup & Recovery

### Automated Backups
```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  retention: 30  # Days
```

### Manual Backup
```bash
# PostgreSQL
kubectl exec healthcare-postgresql-0 -n healthcare-system -- \
  pg_dump -U healthcare healthcare_db > backup.sql

# Neo4j
kubectl exec healthcare-neo4j-0 -n healthcare-system -- \
  neo4j-admin backup --backup-dir=/backups
```

## 🧪 Testing & Validation

### Health Checks
```bash
# Check all pods
kubectl get pods -n healthcare-system

# Test Django application
curl http://healthcare.example.com/health/

# Test database connections
kubectl exec healthcare-django-xxx -n healthcare-system -- \
  python manage.py check --database default
```

### Performance Testing
```bash
# Run load test
kubectl run -it --rm load-test --image=williamyeh/wrk --restart=Never -- \
  wrk -t12 -c400 -d30s http://healthcare-django:8000/
```

## 🛠️ Customization

### Adding Custom Agents
1. Edit `values.yaml` to add agent configuration
2. Create template in `templates/ai-agents/`
3. Deploy with `helm upgrade`

### Modifying Resources
```bash
# Update via command line
helm upgrade healthcare . \
  --set application.django.resources.requests.cpu=2000m

# Update via values file
helm upgrade healthcare . \
  --values custom-values.yaml
```

## 📞 Support & Troubleshooting

### Common Issues

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n healthcare-system
kubectl logs <pod-name> -n healthcare-system
```

**PVC not binding:**
```bash
kubectl get pvc -n healthcare-system
kubectl describe pvc <pvc-name> -n healthcare-system
```

**Service not accessible:**
```bash
kubectl get svc -n healthcare-system
kubectl get ingress -n healthcare-system
```

### Debug Mode
```bash
# Enable debug logging
helm upgrade healthcare . \
  --set application.django.env[0].name=DEBUG \
  --set application.django.env[0].value="True"
```

## 📚 Additional Resources

### Documentation Files
- `README.md` - Full documentation
- `QUICKSTART.md` - Quick start guide
- `values.yaml` - All configuration options
- `production-values.yaml` - Production example

### Helm Commands Reference
```bash
# Install
helm install healthcare .

# Upgrade
helm upgrade healthcare .

# Rollback
helm rollback healthcare

# Uninstall
helm uninstall healthcare

# Get values
helm get values healthcare

# Get status
helm status healthcare

# List releases
helm list -n healthcare-system
```

## 🎯 Next Steps

1. **Review Configuration**
   - Read `values.yaml` thoroughly
   - Customize for your environment
   - Set secure passwords

2. **Deploy to Development**
   - Use `./install.sh` for quick setup
   - Test all components
   - Verify connectivity

3. **Production Planning**
   - Review `production-values.yaml`
   - Plan resource allocation
   - Set up monitoring and alerts
   - Configure backup strategy

4. **Go Live**
   - Deploy to production cluster
   - Configure DNS and ingress
   - Enable monitoring
   - Test disaster recovery

## 📄 License & Support

- **Chart Version:** 1.0.0
- **App Version:** 1.0.0
- **Maintained by:** Healthcare System Team
- **Support:** support@healthcare.example.com

---

**Ready to deploy?** Extract the package and run `./install.sh`!

For detailed instructions, see `README.md` and `QUICKSTART.md`.
