# Healthcare System Helm Chart

A comprehensive Helm chart for deploying a complete Healthcare System with AI agents on Kubernetes.

## Architecture Overview

This Helm chart deploys a full-stack healthcare application with:

- **Application Layer**: Django web app, Celery workers, WebSocket server, static file server
- **AI Agents Layer**: 25+ specialized microservices including LLM, RAG, and domain-specific agents
- **Data Persistence**: PostgreSQL, Neo4j, Redis, RabbitMQ, MinIO
- **Monitoring**: Prometheus, Grafana, Alertmanager
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Ingress**: NGINX Ingress Controller, Cert-Manager, WAF, Kong API Gateway

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- kubectl configured to communicate with your cluster
- Persistent Volume provisioner support (for data persistence)
- Optional: GPU nodes with NVIDIA drivers (for LLM/Imaging agents)
- Optional: StorageClass for fast SSDs (for databases)

## Quick Start

### 1. Add Dependencies

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add elastic https://helm.elastic.co
helm repo update
```

### 2. Create Namespace

```bash
kubectl create namespace healthcare-system
```

### 3. Install the Chart

```bash
# Basic installation
helm install healthcare ./healthcare-k8s-helm \
  --namespace healthcare-system \
  --create-namespace

# With custom values
helm install healthcare ./healthcare-k8s-helm \
  --namespace healthcare-system \
  --values custom-values.yaml
```

### 4. Set Required Secrets

```bash
# Generate strong passwords
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export NEO4J_PASSWORD=$(openssl rand -base64 32)
export DJANGO_SECRET=$(openssl rand -base64 50)
export MINIO_PASSWORD=$(openssl rand -base64 32)

# Install with secrets
helm install healthcare ./healthcare-k8s-helm \
  --namespace healthcare-system \
  --set data.postgresql.auth.password=$POSTGRES_PASSWORD \
  --set data.neo4j.auth.password=$NEO4J_PASSWORD \
  --set application.django.secrets.secretKey=$DJANGO_SECRET \
  --set data.minio.auth.rootPassword=$MINIO_PASSWORD \
  --set monitoring.grafana.adminPassword=$(openssl rand -base64 32)
```

## Configuration

### Global Settings

```yaml
global:
  domain: healthcare.example.com
  environment: production
  imageRegistry: docker.io
  storageClass: fast-ssd
```

### Resource Requirements

**Minimum Cluster Resources:**
- CPU: 100 cores
- Memory: 300GB RAM
- Storage: 3TB
- GPU: 2x NVIDIA A100 (for AI agents)

**Recommended for Production:**
- CPU: 200+ cores
- Memory: 400GB+ RAM
- Storage: 5TB+
- GPU: 4x NVIDIA A100

### Component Configuration

#### Application Layer

Enable/disable Django application and configure autoscaling:

```yaml
application:
  django:
    enabled: true
    replicaCount: 5
    autoscaling:
      enabled: true
      minReplicas: 5
      maxReplicas: 20
```

#### AI Agents

Configure each agent individually:

```yaml
aiAgents:
  llm:
    enabled: true
    replicaCount: 3
    gpu:
      enabled: true
      type: nvidia-tesla-a100
  
  medicalAgents:
    diagnosticAgent:
      enabled: true
      replicaCount: 3
```

#### Data Persistence

Configure databases with replication:

```yaml
data:
  postgresql:
    enabled: true
    architecture: replication
    primary:
      persistence:
        size: 500Gi
    readReplicas:
      replicaCount: 2
```

### Ingress Configuration

```yaml
ingress:
  enabled: true
  className: nginx
  tls:
    enabled: true
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
```

## Installation Examples

### Development Environment

```bash
helm install healthcare ./healthcare-k8s-helm \
  --namespace healthcare-dev \
  --set global.environment=development \
  --set ingress.tls.enabled=false \
  --set monitoring.prometheus.enabled=false \
  --set logging.elasticsearch.enabled=false \
  --set aiAgents.llm.gpu.enabled=false
```

### Production Environment

```bash
helm install healthcare ./healthcare-k8s-helm \
  --namespace healthcare-prod \
  --values production-values.yaml \
  --set-file application.django.secrets.secretKey=./secrets/django-secret.txt \
  --set-file data.postgresql.auth.password=./secrets/postgres-password.txt
```

### Staging with Reduced Resources

```bash
helm install healthcare ./healthcare-k8s-helm \
  --namespace healthcare-staging \
  --set application.django.replicaCount=2 \
  --set application.celery.workers.replicaCount=3 \
  --set data.postgresql.readReplicas.replicaCount=1
```

## Upgrading

```bash
# Upgrade to new version
helm upgrade healthcare ./healthcare-k8s-helm \
  --namespace healthcare-system \
  --reuse-values

# Upgrade with new values
helm upgrade healthcare ./healthcare-k8s-helm \
  --namespace healthcare-system \
  --values updated-values.yaml
```

## Uninstalling

```bash
# Uninstall release
helm uninstall healthcare --namespace healthcare-system

# Delete namespace (caution: deletes all data)
kubectl delete namespace healthcare-system
```

## Monitoring & Observability

### Access Grafana

```bash
kubectl port-forward -n healthcare-system svc/healthcare-grafana 3000:3000
# Open http://localhost:3000
# Username: admin
# Password: (set during installation)
```

### Access Prometheus

```bash
kubectl port-forward -n healthcare-system svc/healthcare-prometheus-server 9090:9090
# Open http://localhost:9090
```

### Access Kibana (Logs)

```bash
kubectl port-forward -n healthcare-system svc/healthcare-kibana 5601:5601
# Open http://localhost:5601
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n healthcare-system
kubectl describe pod <pod-name> -n healthcare-system
kubectl logs <pod-name> -n healthcare-system
```

### Check Services

```bash
kubectl get svc -n healthcare-system
kubectl get ingress -n healthcare-system
```

### Database Connection Issues

```bash
# Check PostgreSQL
kubectl exec -it healthcare-postgresql-0 -n healthcare-system -- psql -U healthcare

# Check Neo4j
kubectl exec -it healthcare-neo4j-0 -n healthcare-system -- cypher-shell

# Check Redis
kubectl exec -it healthcare-redis-master-0 -n healthcare-system -- redis-cli ping
```

### Check Persistent Volumes

```bash
kubectl get pvc -n healthcare-system
kubectl get pv
```

## Backup & Recovery

### Database Backups

```bash
# PostgreSQL backup
kubectl exec healthcare-postgresql-0 -n healthcare-system -- \
  pg_dump -U healthcare healthcare_db > backup.sql

# Neo4j backup
kubectl exec healthcare-neo4j-0 -n healthcare-system -- \
  neo4j-admin backup --backup-dir=/backups --name=graph.db
```

### Restore from Backup

```bash
# PostgreSQL restore
cat backup.sql | kubectl exec -i healthcare-postgresql-0 -n healthcare-system -- \
  psql -U healthcare healthcare_db
```

## Security Considerations

1. **Change all default passwords** before production deployment
2. Enable **TLS/SSL** for all external endpoints
3. Configure **Network Policies** to restrict pod-to-pod communication
4. Use **RBAC** to limit service account permissions
5. Enable **Pod Security Policies**
6. Regularly update container images for security patches
7. Use **secrets management** solutions (e.g., HashiCorp Vault, AWS Secrets Manager)
8. Enable **audit logging** in Kubernetes

## Performance Tuning

### Database Optimization

```yaml
data:
  postgresql:
    primary:
      resources:
        requests:
          cpu: 4000m
          memory: 16Gi
      extraEnvVars:
        - name: POSTGRES_MAX_CONNECTIONS
          value: "500"
        - name: POSTGRES_SHARED_BUFFERS
          value: "4GB"
```

### Application Scaling

```yaml
application:
  django:
    autoscaling:
      enabled: true
      minReplicas: 10
      maxReplicas: 50
      targetCPUUtilizationPercentage: 60
```

## Contributing

For issues, questions, or contributions, please refer to the project repository.

## License

Copyright © 2025 Healthcare System Team

## Support

For support, please contact: support@healthcare.example.com

## Architecture Diagram

Refer to the included `kubernetes_pods_fixed.drawio` file for a visual representation of the complete architecture.

## Values Reference

See `values.yaml` for a complete list of configurable parameters.

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.domain` | Main domain for the application | `healthcare.example.com` |
| `ingress.enabled` | Enable ingress controller | `true` |
| `application.django.replicaCount` | Number of Django pods | `5` |
| `aiAgents.llm.enabled` | Enable LLM service | `true` |
| `data.postgresql.enabled` | Enable PostgreSQL | `true` |
| `monitoring.prometheus.enabled` | Enable Prometheus monitoring | `true` |

## FAQ

**Q: Can I deploy only certain components?**
A: Yes, each major component can be enabled/disabled via values.yaml

**Q: How do I scale individual agents?**
A: Adjust `replicaCount` for each agent in values.yaml or use kubectl scale

**Q: What if I don't have GPU nodes?**
A: Set `aiAgents.llm.gpu.enabled=false` and the LLM will run on CPU (slower)

**Q: Can I use external databases?**
A: Yes, disable internal databases and provide connection strings via secrets

**Q: How do I enable high availability?**
A: Increase replica counts, enable autoscaling, and use ReadWriteMany volumes
