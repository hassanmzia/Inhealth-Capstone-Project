#!/bin/bash

# Healthcare System Kubernetes Deployment Script
# This script helps automate the deployment of the Healthcare System on Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="healthcare-system"
RELEASE_NAME="healthcare"
CHART_PATH="./healthcare-k8s-helm"

echo -e "${GREEN}Healthcare System Kubernetes Deployment${NC}"
echo "=========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}ERROR: kubectl is not installed${NC}"
    exit 1
fi

# Check helm
if ! command -v helm &> /dev/null; then
    echo -e "${RED}ERROR: helm is not installed${NC}"
    exit 1
fi

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}ERROR: Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Add Helm repositories
echo "Adding Helm repositories..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add elastic https://helm.elastic.co
helm repo update
echo -e "${GREEN}✓ Helm repositories added${NC}"
echo ""

# Prompt for environment
echo "Select deployment environment:"
echo "1) Development (minimal resources)"
echo "2) Staging (medium resources)"
echo "3) Production (full resources)"
read -p "Enter choice [1-3]: " env_choice

VALUES_FILE=""
case $env_choice in
    1)
        ENV="development"
        echo -e "${YELLOW}Deploying for Development environment${NC}"
        ;;
    2)
        ENV="staging"
        echo -e "${YELLOW}Deploying for Staging environment${NC}"
        ;;
    3)
        ENV="production"
        VALUES_FILE="production-values.yaml"
        echo -e "${YELLOW}Deploying for Production environment${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
echo ""

# Generate secrets
echo "Generating secure passwords..."
POSTGRES_PASSWORD=$(openssl rand -base64 32)
NEO4J_PASSWORD=$(openssl rand -base64 32)
DJANGO_SECRET=$(openssl rand -base64 50)
MINIO_PASSWORD=$(openssl rand -base64 32)
RABBITMQ_PASSWORD=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -base64 32)

echo -e "${GREEN}✓ Passwords generated${NC}"
echo ""

# Prompt for domain
read -p "Enter your domain (e.g., healthcare.example.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    DOMAIN="healthcare.example.com"
    echo -e "${YELLOW}Using default domain: $DOMAIN${NC}"
fi
echo ""

# Create namespace
echo "Creating namespace: $NAMESPACE"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Namespace created${NC}"
echo ""

# Build helm install command
HELM_CMD="helm install $RELEASE_NAME $CHART_PATH \
  --namespace $NAMESPACE \
  --set global.domain=$DOMAIN \
  --set global.environment=$ENV \
  --set data.postgresql.auth.password=$POSTGRES_PASSWORD \
  --set data.neo4j.auth.password=$NEO4J_PASSWORD \
  --set application.django.secrets.secretKey=$DJANGO_SECRET \
  --set data.minio.auth.rootPassword=$MINIO_PASSWORD \
  --set data.rabbitmq.auth.password=$RABBITMQ_PASSWORD \
  --set monitoring.grafana.adminPassword=$GRAFANA_PASSWORD"

# Add values file for production
if [ ! -z "$VALUES_FILE" ]; then
    HELM_CMD="$HELM_CMD --values $VALUES_FILE"
fi

# Development specific settings
if [ "$ENV" == "development" ]; then
    HELM_CMD="$HELM_CMD \
      --set ingress.tls.enabled=false \
      --set monitoring.prometheus.enabled=false \
      --set logging.elasticsearch.enabled=false \
      --set aiAgents.llm.gpu.enabled=false \
      --set application.django.replicaCount=2 \
      --set application.celery.workers.replicaCount=2"
fi

# Staging specific settings
if [ "$ENV" == "staging" ]; then
    HELM_CMD="$HELM_CMD \
      --set application.django.replicaCount=3 \
      --set application.celery.workers.replicaCount=4"
fi

# Install
echo "Installing Healthcare System..."
echo ""
eval $HELM_CMD

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Healthcare System installed successfully!${NC}"
    echo ""
    
    # Save credentials
    CREDS_FILE="healthcare-credentials-$(date +%Y%m%d-%H%M%S).txt"
    cat > $CREDS_FILE <<EOF
Healthcare System Credentials
Generated: $(date)
Environment: $ENV
Namespace: $NAMESPACE
Domain: $DOMAIN

=== Database Credentials ===
PostgreSQL Password: $POSTGRES_PASSWORD
Neo4j Password: $NEO4J_PASSWORD
RabbitMQ Password: $RABBITMQ_PASSWORD
MinIO Root Password: $MINIO_PASSWORD

=== Application Secrets ===
Django Secret Key: $DJANGO_SECRET

=== Monitoring ===
Grafana Admin Password: $GRAFANA_PASSWORD

=== Connection Strings ===
PostgreSQL: postgresql://healthcare:$POSTGRES_PASSWORD@$RELEASE_NAME-postgresql:5432/healthcare_db
Neo4j: bolt://neo4j:$NEO4J_PASSWORD@$RELEASE_NAME-neo4j:7687
Redis: redis://$RELEASE_NAME-redis-master:6379
RabbitMQ: amqp://healthcare:$RABBITMQ_PASSWORD@$RELEASE_NAME-rabbitmq:5672/
MinIO: http://$RELEASE_NAME-minio:9000 (Access: admin / $MINIO_PASSWORD)

IMPORTANT: Store these credentials securely and delete this file after saving them elsewhere.
EOF
    
    echo -e "${YELLOW}Credentials saved to: $CREDS_FILE${NC}"
    echo -e "${RED}⚠️  IMPORTANT: Store these credentials securely!${NC}"
    echo ""
    
    # Display next steps
    echo "Next steps:"
    echo "1. Wait for all pods to be ready:"
    echo "   kubectl get pods -n $NAMESPACE -w"
    echo ""
    echo "2. Check the status:"
    echo "   helm status $RELEASE_NAME -n $NAMESPACE"
    echo ""
    echo "3. Access Grafana (monitoring):"
    echo "   kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-grafana 3000:3000"
    echo "   URL: http://localhost:3000"
    echo "   Username: admin"
    echo "   Password: (see $CREDS_FILE)"
    echo ""
    echo "4. Access the application:"
    if [ "$ENV" == "development" ]; then
        echo "   kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-django 8000:8000"
        echo "   URL: http://localhost:8000"
    else
        echo "   URL: https://$DOMAIN"
    fi
    echo ""
    echo "5. View logs:"
    echo "   kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=healthcare --tail=100 -f"
    echo ""
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi
