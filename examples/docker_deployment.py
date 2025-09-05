#!/usr/bin/env python3
"""
Docker Deployment Example - Federal Reserve ETL Pipeline

This script demonstrates containerized deployment patterns for the ETL pipeline,
including Docker configurations and orchestration examples.
"""

import os
import sys
from pathlib import Path
from textwrap import dedent


def create_dockerfile():
    """Create production-ready Dockerfile"""
    dockerfile_content = dedent("""
    # Federal Reserve ETL Pipeline - Production Dockerfile
    FROM python:3.11-slim as base
    
    # Set environment variables
    ENV PYTHONUNBUFFERED=1 \\
        PYTHONDONTWRITEBYTECODE=1 \\
        PIP_NO_CACHE_DIR=1 \\
        PIP_DISABLE_PIP_VERSION_CHECK=1
    
    # Create app user for security
    RUN groupadd -r appuser && useradd -r -g appuser appuser
    
    # Install system dependencies
    RUN apt-get update && apt-get install -y \\
        gcc \\
        g++ \\
        curl \\
        && rm -rf /var/lib/apt/lists/*
    
    # Set working directory
    WORKDIR /app
    
    # Copy requirements first for better caching
    COPY requirements.txt requirements-dev.txt ./
    
    # Install Python dependencies
    RUN pip install --upgrade pip && \\
        pip install -r requirements.txt && \\
        pip install gunicorn supervisor
    
    # Copy application code
    COPY src/ ./src/
    COPY setup.py MANIFEST.in ./
    
    # Install package in development mode
    RUN pip install -e .
    
    # Create directories for logs and data
    RUN mkdir -p /app/logs /app/data /app/output && \\
        chown -R appuser:appuser /app
    
    # Copy configuration files
    COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
    COPY docker/entrypoint.sh /entrypoint.sh
    RUN chmod +x /entrypoint.sh
    
    # Switch to app user
    USER appuser
    
    # Health check
    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
        CMD python -c "from src.federal_reserve_etl import create_data_source; create_data_source('fred').connect()" || exit 1
    
    # Expose port for potential web interface
    EXPOSE 8000
    
    # Entry point
    ENTRYPOINT ["/entrypoint.sh"]
    CMD ["pipeline"]
    """)
    
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile_content.strip())
    
    print("✅ Created: Dockerfile")


def create_docker_compose():
    """Create Docker Compose configuration for multi-service deployment"""
    compose_content = dedent("""
    version: '3.8'
    
    services:
      federal-reserve-etl:
        build:
          context: .
          dockerfile: Dockerfile
        container_name: federal-reserve-etl
        restart: unless-stopped
        environment:
          - FRED_API_KEY=${FRED_API_KEY}
          - HAVER_USERNAME=${HAVER_USERNAME}
          - HAVER_PASSWORD=${HAVER_PASSWORD}
          - LOG_LEVEL=INFO
          - PYTHONPATH=/app/src
        volumes:
          - ./logs:/app/logs
          - ./data:/app/data
          - ./output:/app/output
        networks:
          - etl-network
        depends_on:
          - redis
          - postgres
        command: ["pipeline", "--schedule", "daily"]
    
      redis:
        image: redis:7-alpine
        container_name: etl-redis
        restart: unless-stopped
        ports:
          - "6379:6379"
        volumes:
          - redis_data:/data
        networks:
          - etl-network
        command: redis-server --appendonly yes
    
      postgres:
        image: postgres:15-alpine
        container_name: etl-postgres
        restart: unless-stopped
        environment:
          - POSTGRES_DB=federal_reserve_etl
          - POSTGRES_USER=etl_user
          - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
        ports:
          - "5432:5432"
        volumes:
          - postgres_data:/var/lib/postgresql/data
          - ./docker/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
        networks:
          - etl-network
    
      scheduler:
        build:
          context: .
          dockerfile: Dockerfile
        container_name: etl-scheduler
        restart: unless-stopped
        environment:
          - FRED_API_KEY=${FRED_API_KEY}
          - HAVER_USERNAME=${HAVER_USERNAME}
          - HAVER_PASSWORD=${HAVER_PASSWORD}
          - LOG_LEVEL=INFO
          - REDIS_URL=redis://redis:6379/0
          - DATABASE_URL=postgresql://etl_user:${POSTGRES_PASSWORD:-changeme}@postgres:5432/federal_reserve_etl
        volumes:
          - ./logs:/app/logs
          - ./data:/app/data
          - ./output:/app/output
        networks:
          - etl-network
        depends_on:
          - redis
          - postgres
        command: ["scheduler"]
    
      monitoring:
        image: prom/prometheus:latest
        container_name: etl-monitoring
        restart: unless-stopped
        ports:
          - "9090:9090"
        volumes:
          - ./docker/prometheus.yml:/etc/prometheus/prometheus.yml:ro
          - prometheus_data:/prometheus
        networks:
          - etl-network
        command:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--storage.tsdb.path=/prometheus'
          - '--web.console.libraries=/etc/prometheus/console_libraries'
          - '--web.console.templates=/etc/prometheus/consoles'
    
    volumes:
      redis_data:
      postgres_data:
      prometheus_data:
    
    networks:
      etl-network:
        driver: bridge
    """)
    
    with open('docker-compose.yml', 'w') as f:
        f.write(compose_content.strip())
    
    print("✅ Created: docker-compose.yml")


def create_docker_support_files():
    """Create supporting Docker configuration files"""
    
    # Create docker directory
    docker_dir = Path('docker')
    docker_dir.mkdir(exist_ok=True)
    
    # Entrypoint script
    entrypoint_content = dedent("""
    #!/bin/bash
    set -e
    
    # Wait for dependencies to be ready
    wait_for_service() {
        local host=$1
        local port=$2
        local service_name=$3
        
        echo "Waiting for $service_name to be ready..."
        while ! nc -z $host $port; do
            sleep 1
        done
        echo "$service_name is ready!"
    }
    
    # Initialize logging
    python -c "from src.federal_reserve_etl.utils.logging import setup_logging; setup_logging()"
    
    case "$1" in
        pipeline)
            echo "Starting Federal Reserve ETL Pipeline..."
            if [ "$2" = "--schedule" ]; then
                echo "Running in scheduled mode: $3"
                python -m src.federal_reserve_etl.scheduler --mode=$3
            else
                echo "Running one-time extraction..."
                python -m src.federal_reserve_etl.cli extract --source=fred --variables=FEDFUNDS,DGS10,UNRATE
            fi
            ;;
        scheduler)
            echo "Starting ETL Scheduler..."
            wait_for_service redis 6379 "Redis"
            wait_for_service postgres 5432 "PostgreSQL"
            python -m src.federal_reserve_etl.scheduler
            ;;
        web)
            echo "Starting Web Interface..."
            gunicorn --bind 0.0.0.0:8000 src.federal_reserve_etl.web:app
            ;;
        worker)
            echo "Starting Background Worker..."
            wait_for_service redis 6379 "Redis"
            python -m src.federal_reserve_etl.worker
            ;;
        test)
            echo "Running tests..."
            pytest tests/ -v --cov=src/federal_reserve_etl
            ;;
        shell)
            echo "Starting interactive shell..."
            python
            ;;
        *)
            echo "Available commands: pipeline, scheduler, web, worker, test, shell"
            echo "Usage: docker run federal-reserve-etl [command] [options]"
            exit 1
            ;;
    esac
    """)
    
    with open(docker_dir / 'entrypoint.sh', 'w') as f:
        f.write(entrypoint_content.strip())
    
    # Supervisor configuration
    supervisord_content = dedent("""
    [supervisord]
    nodaemon=true
    user=appuser
    logfile=/app/logs/supervisord.log
    pidfile=/app/logs/supervisord.pid
    
    [program:etl-pipeline]
    command=python -m src.federal_reserve_etl.scheduler
    directory=/app
    user=appuser
    autostart=true
    autorestart=true
    redirect_stderr=true
    stdout_logfile=/app/logs/pipeline.log
    stdout_logfile_maxbytes=10MB
    stdout_logfile_backups=5
    
    [program:health-check]
    command=python -m src.federal_reserve_etl.health_check
    directory=/app
    user=appuser
    autostart=true
    autorestart=true
    redirect_stderr=true
    stdout_logfile=/app/logs/health_check.log
    """)
    
    with open(docker_dir / 'supervisord.conf', 'w') as f:
        f.write(supervisord_content.strip())
    
    # Database initialization
    init_sql_content = dedent("""
    -- Initialize Federal Reserve ETL Database
    
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Create tables for data storage and job tracking
    CREATE TABLE IF NOT EXISTS extraction_jobs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        job_type VARCHAR(50) NOT NULL,
        source VARCHAR(20) NOT NULL,
        variables TEXT[] NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        error_message TEXT,
        result_location TEXT
    );
    
    CREATE TABLE IF NOT EXISTS extracted_data (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        job_id UUID REFERENCES extraction_jobs(id),
        variable_code VARCHAR(50) NOT NULL,
        observation_date DATE NOT NULL,
        value DECIMAL,
        source VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(variable_code, observation_date, source)
    );
    
    CREATE INDEX idx_extraction_jobs_status ON extraction_jobs(status);
    CREATE INDEX idx_extraction_jobs_created ON extraction_jobs(created_at);
    CREATE INDEX idx_extracted_data_variable ON extracted_data(variable_code);
    CREATE INDEX idx_extracted_data_date ON extracted_data(observation_date);
    
    -- Grant permissions
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO etl_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO etl_user;
    """)
    
    with open(docker_dir / 'init.sql', 'w') as f:
        f.write(init_sql_content.strip())
    
    # Prometheus configuration
    prometheus_content = dedent("""
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    scrape_configs:
      - job_name: 'federal-reserve-etl'
        static_configs:
          - targets: ['federal-reserve-etl:8000']
        metrics_path: '/metrics'
        scrape_interval: 30s
    
      - job_name: 'redis'
        static_configs:
          - targets: ['redis:6379']
    
      - job_name: 'postgres'
        static_configs:
          - targets: ['postgres:5432']
    """)
    
    with open(docker_dir / 'prometheus.yml', 'w') as f:
        f.write(prometheus_content.strip())
    
    print("✅ Created Docker support files in docker/ directory")


def create_kubernetes_manifests():
    """Create Kubernetes deployment manifests"""
    
    k8s_dir = Path('k8s')
    k8s_dir.mkdir(exist_ok=True)
    
    # Namespace
    namespace_content = dedent("""
    apiVersion: v1
    kind: Namespace
    metadata:
      name: federal-reserve-etl
      labels:
        name: federal-reserve-etl
    """)
    
    with open(k8s_dir / 'namespace.yaml', 'w') as f:
        f.write(namespace_content.strip())
    
    # ConfigMap
    configmap_content = dedent("""
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: etl-config
      namespace: federal-reserve-etl
    data:
      LOG_LEVEL: "INFO"
      REDIS_URL: "redis://redis-service:6379/0"
      DATABASE_URL: "postgresql://etl_user:changeme@postgres-service:5432/federal_reserve_etl"
      SCHEDULE_INTERVAL: "3600"  # 1 hour
    """)
    
    with open(k8s_dir / 'configmap.yaml', 'w') as f:
        f.write(configmap_content.strip())
    
    # Secret
    secret_content = dedent("""
    apiVersion: v1
    kind: Secret
    metadata:
      name: etl-secrets
      namespace: federal-reserve-etl
    type: Opaque
    data:
      # Base64 encoded values (replace with actual encoded secrets)
      fred-api-key: <base64-encoded-fred-api-key>
      haver-username: <base64-encoded-haver-username>
      haver-password: <base64-encoded-haver-password>
      postgres-password: <base64-encoded-postgres-password>
    """)
    
    with open(k8s_dir / 'secrets.yaml', 'w') as f:
        f.write(secret_content.strip())
    
    # Deployment
    deployment_content = dedent("""
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: federal-reserve-etl
      namespace: federal-reserve-etl
      labels:
        app: federal-reserve-etl
    spec:
      replicas: 2
      selector:
        matchLabels:
          app: federal-reserve-etl
      template:
        metadata:
          labels:
            app: federal-reserve-etl
        spec:
          containers:
          - name: etl-pipeline
            image: federal-reserve-etl:latest
            imagePullPolicy: IfNotPresent
            command: ["/entrypoint.sh", "scheduler"]
            env:
            - name: FRED_API_KEY
              valueFrom:
                secretKeyRef:
                  name: etl-secrets
                  key: fred-api-key
            - name: HAVER_USERNAME
              valueFrom:
                secretKeyRef:
                  name: etl-secrets
                  key: haver-username
            - name: HAVER_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: etl-secrets
                  key: haver-password
            envFrom:
            - configMapRef:
                name: etl-config
            resources:
              requests:
                memory: "256Mi"
                cpu: "250m"
              limits:
                memory: "512Mi"
                cpu: "500m"
            volumeMounts:
            - name: logs-volume
              mountPath: /app/logs
            - name: data-volume
              mountPath: /app/data
            livenessProbe:
              exec:
                command:
                - python
                - -c
                - "from src.federal_reserve_etl import create_data_source; create_data_source('fred').connect()"
              initialDelaySeconds: 30
              periodSeconds: 60
            readinessProbe:
              exec:
                command:
                - python
                - -c
                - "import sys; sys.exit(0)"
              initialDelaySeconds: 5
              periodSeconds: 10
          volumes:
          - name: logs-volume
            persistentVolumeClaim:
              claimName: etl-logs-pvc
          - name: data-volume
            persistentVolumeClaim:
              claimName: etl-data-pvc
          restartPolicy: Always
    """)
    
    with open(k8s_dir / 'deployment.yaml', 'w') as f:
        f.write(deployment_content.strip())
    
    # CronJob for scheduled extractions
    cronjob_content = dedent("""
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: daily-etl-extraction
      namespace: federal-reserve-etl
    spec:
      schedule: "0 6 * * *"  # Daily at 6 AM UTC
      jobTemplate:
        spec:
          template:
            spec:
              containers:
              - name: etl-extraction
                image: federal-reserve-etl:latest
                imagePullPolicy: IfNotPresent
                command: ["/entrypoint.sh", "pipeline"]
                env:
                - name: FRED_API_KEY
                  valueFrom:
                    secretKeyRef:
                      name: etl-secrets
                      key: fred-api-key
                envFrom:
                - configMapRef:
                    name: etl-config
                resources:
                  requests:
                    memory: "128Mi"
                    cpu: "100m"
                  limits:
                    memory: "256Mi"
                    cpu: "200m"
              restartPolicy: OnFailure
          backoffLimit: 3
      successfulJobsHistoryLimit: 3
      failedJobsHistoryLimit: 1
    """)
    
    with open(k8s_dir / 'cronjob.yaml', 'w') as f:
        f.write(cronjob_content.strip())
    
    print("✅ Created Kubernetes manifests in k8s/ directory")


def create_deployment_scripts():
    """Create deployment helper scripts"""
    
    # Docker build script
    docker_build_content = dedent("""
    #!/bin/bash
    set -e
    
    echo "🐳 Building Federal Reserve ETL Docker Image..."
    
    # Build the image
    docker build -t federal-reserve-etl:latest .
    
    # Tag for different environments
    docker tag federal-reserve-etl:latest federal-reserve-etl:dev
    docker tag federal-reserve-etl:latest federal-reserve-etl:$(date +%Y%m%d)
    
    echo "✅ Docker image built successfully!"
    echo "Available tags:"
    docker images federal-reserve-etl
    """)
    
    with open('build_docker.sh', 'w') as f:
        f.write(docker_build_content.strip())
    os.chmod('build_docker.sh', 0o755)
    
    # Docker run script
    docker_run_content = dedent("""
    #!/bin/bash
    set -e
    
    # Check for required environment variables
    if [ -z "$FRED_API_KEY" ]; then
        echo "❌ FRED_API_KEY environment variable is required"
        exit 1
    fi
    
    echo "🚀 Starting Federal Reserve ETL Pipeline..."
    
    # Create necessary directories
    mkdir -p logs data output
    
    # Run the container
    docker run -d \\
        --name federal-reserve-etl \\
        --restart unless-stopped \\
        -e FRED_API_KEY="$FRED_API_KEY" \\
        -e HAVER_USERNAME="$HAVER_USERNAME" \\
        -e HAVER_PASSWORD="$HAVER_PASSWORD" \\
        -e LOG_LEVEL=INFO \\
        -v $(pwd)/logs:/app/logs \\
        -v $(pwd)/data:/app/data \\
        -v $(pwd)/output:/app/output \\
        -p 8000:8000 \\
        federal-reserve-etl:latest pipeline
    
    echo "✅ Container started successfully!"
    echo "Container ID: $(docker ps -l -q)"
    echo "Logs: docker logs -f federal-reserve-etl"
    """)
    
    with open('run_docker.sh', 'w') as f:
        f.write(docker_run_content.strip())
    os.chmod('run_docker.sh', 0o755)
    
    # Kubernetes deploy script
    k8s_deploy_content = dedent("""
    #!/bin/bash
    set -e
    
    echo "☸️  Deploying Federal Reserve ETL to Kubernetes..."
    
    # Apply manifests in order
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secrets.yaml
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/cronjob.yaml
    
    # Wait for deployment
    echo "⏳ Waiting for deployment to be ready..."
    kubectl rollout status deployment/federal-reserve-etl -n federal-reserve-etl
    
    # Show status
    echo "✅ Deployment completed!"
    kubectl get all -n federal-reserve-etl
    """)
    
    with open('deploy_k8s.sh', 'w') as f:
        f.write(k8s_deploy_content.strip())
    os.chmod('deploy_k8s.sh', 0o755)
    
    print("✅ Created deployment scripts (build_docker.sh, run_docker.sh, deploy_k8s.sh)")


def create_env_template():
    """Create environment template file"""
    env_template_content = dedent("""
    # Federal Reserve ETL Pipeline - Environment Configuration
    # Copy this file to .env and fill in your actual values
    
    # FRED API Configuration (Required)
    FRED_API_KEY=your_32_character_fred_api_key_here
    
    # Haver Analytics Configuration (Optional)
    HAVER_USERNAME=your_haver_username
    HAVER_PASSWORD=your_haver_password
    
    # Pipeline Configuration
    LOG_LEVEL=INFO
    FRED_RATE_LIMIT=120
    HAVER_RATE_LIMIT=10
    
    # Database Configuration (for Docker/K8s deployments)
    POSTGRES_PASSWORD=secure_password_here
    REDIS_URL=redis://localhost:6379/0
    DATABASE_URL=postgresql://etl_user:secure_password_here@localhost:5432/federal_reserve_etl
    
    # Scheduling Configuration
    SCHEDULE_INTERVAL=3600  # 1 hour in seconds
    ENABLE_SCHEDULER=true
    
    # Monitoring Configuration
    ENABLE_METRICS=true
    METRICS_PORT=8000
    """)
    
    with open('.env.template', 'w') as f:
        f.write(env_template_content.strip())
    
    print("✅ Created: .env.template")


def main():
    """Create all Docker deployment files"""
    print("🐳 Creating Docker Deployment Configuration")
    print("=" * 50)
    
    try:
        create_dockerfile()
        create_docker_compose()
        create_docker_support_files()
        create_kubernetes_manifests()
        create_deployment_scripts()
        create_env_template()
        
        print("\n🎉 Docker deployment configuration created successfully!")
        print("\n📁 Files created:")
        print("   - Dockerfile")
        print("   - docker-compose.yml")
        print("   - docker/ (support files)")
        print("   - k8s/ (Kubernetes manifests)")
        print("   - build_docker.sh, run_docker.sh, deploy_k8s.sh")
        print("   - .env.template")
        
        print("\n🚀 Next steps:")
        print("   1. Copy .env.template to .env and configure your API keys")
        print("   2. Run: ./build_docker.sh")
        print("   3. For simple deployment: ./run_docker.sh")
        print("   4. For full stack: docker-compose up -d")
        print("   5. For Kubernetes: ./deploy_k8s.sh")
        
        return 0
        
    except Exception as e:
        print(f"❌ Failed to create deployment configuration: {e}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)