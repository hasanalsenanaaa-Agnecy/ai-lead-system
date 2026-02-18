#!/bin/bash
# =============================================================================
# AI Lead System - Production Deployment Script
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Configuration
# =============================================================================
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

# =============================================================================
# Pre-flight Checks
# =============================================================================
preflight_checks() {
    log_info "Running pre-flight checks..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if .env.prod exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found."
        log_info "Copy .env.prod.example to .env.prod and fill in your values."
        exit 1
    fi

    # Check required environment variables
    source "$ENV_FILE"
    required_vars=("DOMAIN" "POSTGRES_PASSWORD" "SECRET_KEY" "ANTHROPIC_API_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set."
            exit 1
        fi
    done

    log_info "Pre-flight checks passed!"
}

# =============================================================================
# Database Backup
# =============================================================================
backup_database() {
    log_info "Creating database backup..."
    
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"
    
    docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE" 2>/dev/null || true
    
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        log_info "Backup created: $BACKUP_FILE"
    else
        log_warn "No existing database to backup (this is normal for first deployment)"
        rm -f "$BACKUP_FILE"
    fi
}

# =============================================================================
# Build & Deploy
# =============================================================================
build_images() {
    log_info "Building Docker images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --no-cache
}

deploy_services() {
    log_info "Deploying services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
}

run_migrations() {
    log_info "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" exec -T api alembic upgrade head
}

# =============================================================================
# Health Checks
# =============================================================================
health_check() {
    log_info "Running health checks..."
    
    # Wait for services to start
    sleep 10
    
    # Check API health
    API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
    if [ "$API_HEALTH" == "200" ]; then
        log_info "API is healthy"
    else
        log_error "API health check failed (HTTP $API_HEALTH)"
        docker-compose -f "$COMPOSE_FILE" logs api --tail=50
        exit 1
    fi
    
    # Check frontend health
    FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health || echo "000")
    if [ "$FRONTEND_HEALTH" == "200" ]; then
        log_info "Frontend is healthy"
    else
        log_warn "Frontend health check returned HTTP $FRONTEND_HEALTH"
    fi
}

# =============================================================================
# Cleanup
# =============================================================================
cleanup() {
    log_info "Cleaning up old images..."
    docker image prune -f
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo "=============================================="
    echo "  AI Lead System - Production Deployment"
    echo "=============================================="
    echo ""
    
    case "${1:-deploy}" in
        deploy)
            preflight_checks
            backup_database
            build_images
            deploy_services
            run_migrations
            health_check
            cleanup
            log_info "Deployment complete!"
            ;;
        
        update)
            log_info "Updating services..."
            preflight_checks
            backup_database
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
            deploy_services
            run_migrations
            health_check
            log_info "Update complete!"
            ;;
        
        restart)
            log_info "Restarting services..."
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
            health_check
            ;;
        
        stop)
            log_info "Stopping services..."
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
            ;;
        
        logs)
            docker-compose -f "$COMPOSE_FILE" logs -f "${2:-}"
            ;;
        
        status)
            docker-compose -f "$COMPOSE_FILE" ps
            ;;
        
        backup)
            backup_database
            ;;
        
        *)
            echo "Usage: $0 {deploy|update|restart|stop|logs|status|backup}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Full deployment (build + deploy + migrate)"
            echo "  update   - Pull latest images and redeploy"
            echo "  restart  - Restart all services"
            echo "  stop     - Stop all services"
            echo "  logs     - View logs (optionally specify service name)"
            echo "  status   - Show service status"
            echo "  backup   - Create database backup"
            exit 1
            ;;
    esac
}

main "$@"
