#!/bin/bash
set -e

# ===== CONFIGURATION =====
# GCloud/K8s
GCLOUD_PROJECT="rcvrd-1777d"
GKE_CLUSTER="prod-k8s-cluster"
GKE_ZONE="us-central1"
K8S_NAMESPACE="apps"
CNPG_CLUSTER_NAME="pg-cluster"
DATABASE_NAME="backend"

# Azure
AZURE_SSH_USER="azureuser"
AZURE_VM_IP="172.173.216.167"
DOCKER_COMPOSE_PATH="/opt/rcvd/prod"  # where docker compose --project-name prodenv --env-file .env.prod.yml is
POSTGRES_CONTAINER_NAME="postgres"  # or whatever your container is named
AZURE_DB_USER="postgres"
AZURE_DB_NAME="backend"

# Local
DUMP_FILE="data_migration_$(date +%Y%m%d_%H%M%S).backup"

# ===== STEP 1: Setup GCloud & Get Credentials =====
echo "=========================================="
echo "Step 1: Setting up GCloud and K8s access"
echo "=========================================="

gcloud config set project $GCLOUD_PROJECT
gcloud container clusters get-credentials $GKE_CLUSTER --zone $GKE_ZONE

echo "Retrieving database credentials from CNPG secret..."
DB_USER=$(kubectl get secret ${CNPG_CLUSTER_NAME}-app -n $K8S_NAMESPACE \
  -o jsonpath='{.data.username}' | base64 -d)
DB_PASSWORD=$(kubectl get secret ${CNPG_CLUSTER_NAME}-app -n $K8S_NAMESPACE \
  -o jsonpath='{.data.password}' | base64 -d)

if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "❌ Failed to retrieve database credentials"
    exit 1
fi

echo "✅ Database user: $DB_USER"

# ===== STEP 2: Find Primary Pod =====
echo ""
echo "=========================================="
echo "Step 2: Finding primary pod"
echo "=========================================="

PRIMARY_POD=$(kubectl get pod -n $K8S_NAMESPACE \
  -l "cnpg.io/cluster=${CNPG_CLUSTER_NAME},role=primary" \
  -o jsonpath='{.items[0].metadata.name}')

if [ -z "$PRIMARY_POD" ]; then
    echo "❌ Could not find primary pod"
    kubectl get pods -n $K8S_NAMESPACE -l "cnpg.io/cluster=${CNPG_CLUSTER_NAME}"
    exit 1
fi

echo "✅ Primary pod: $PRIMARY_POD"

POD_STATUS=$(kubectl get pod $PRIMARY_POD -n $K8S_NAMESPACE -o jsonpath='{.status.phase}')
if [ "$POD_STATUS" != "Running" ]; then
    echo "❌ Pod is not running (status: $POD_STATUS)"
    exit 1
fi

echo "✅ Pod is running"

# ===== STEP 3: Dump Data Directly from Pod =====
echo ""
echo "=========================================="
echo "Step 3: Dumping data directly from pod"
echo "=========================================="

echo "Running pg_dump inside pod and streaming to local file..."
echo "Database: $DATABASE_NAME"
echo "Output: $DUMP_FILE"
echo ""
echo "This may take a while for large databases..."

# Run pg_dump inside the pod and stream output to local file
kubectl exec -n $K8S_NAMESPACE $PRIMARY_POD -- \
  bash -c "PGPASSWORD='$DB_PASSWORD' pg_dump \
    -h localhost \
    -U $DB_USER \
    -d $DATABASE_NAME \
    --data-only \
    --no-owner \
    --no-privileges \
    -Fc \
    -Z 6" \
  > $DUMP_FILE

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ pg_dump failed"
    echo "Recent pod logs:"
    kubectl logs --tail=30 $PRIMARY_POD -n $K8S_NAMESPACE
    exit 1
fi

echo ""
echo "✅ Dump completed: $DUMP_FILE"
echo "   Size: $(du -h $DUMP_FILE | cut -f1)"

# Verify dump integrity
echo "Verifying dump file..."
if ! pg_restore --list $DUMP_FILE >/dev/null 2>&1; then
    echo "❌ Dump file is corrupted!"
    exit 1
fi

echo "✅ Dump file verified"

# ===== STEP 4: Transfer to Azure =====
echo ""
echo "=========================================="
echo "Step 4: Transferring to Azure VM"
echo "=========================================="

echo "Transferring $DUMP_FILE to Azure..."

scp ./$DUMP_FILE ${AZURE_SSH_USER}@${AZURE_VM_IP}:/tmp/

if [ $? -ne 0 ]; then
    echo "❌ Transfer failed"
    exit 1
fi

echo "✅ Transfer complete"

# Verify file size
LOCAL_SIZE=$(stat -f%z $DUMP_FILE 2>/dev/null || stat -c%s $DUMP_FILE 2>/dev/null)
REMOTE_SIZE=$(ssh ${AZURE_SSH_USER}@${AZURE_VM_IP} \
  "stat -f%z /tmp/$DUMP_FILE 2>/dev/null || stat -c%s /tmp/$DUMP_FILE 2>/dev/null")

if [ "$LOCAL_SIZE" != "$REMOTE_SIZE" ]; then
    echo "❌ File size mismatch! Local: $LOCAL_SIZE, Remote: $REMOTE_SIZE"
    exit 1
fi

echo "✅ File verified on remote"

# ===== STEP 5: Restore on Azure =====
echo ""
echo "=========================================="
echo "Step 5: Restoring on Azure"
echo "=========================================="

REMOTE_SCRIPT=$(cat << 'ENDSCRIPT'
#!/bin/bash
set -e

DUMP_FILE="$1"
DOCKER_COMPOSE_PATH="$2"
POSTGRES_CONTAINER_NAME="$3"
AZURE_DB_USER="$4"
AZURE_DB_NAME="$5"

echo "Configuration:"
echo "  Dump: $DUMP_FILE"
echo "  Path: $DOCKER_COMPOSE_PATH"
echo "  Container: $POSTGRES_CONTAINER_NAME"
echo "  Database: $AZURE_DB_NAME"
echo ""

cd "$DOCKER_COMPOSE_PATH"

# Verify container is running
if ! docker compose --project-name prodenv --env-file .env.prod ps | grep -q "$POSTGRES_CONTAINER_NAME.*Up"; then
    echo "❌ Container not running"
    docker compose --project-name prodenv --env-file .env.prod ps
    exit 1
fi

echo "Step 1: Truncating tables..."
docker compose --project-name prodenv --env-file .env.prod exec -T $POSTGRES_CONTAINER_NAME psql -U $AZURE_DB_USER -d $AZURE_DB_NAME << 'ENDPSQL'
DO $$ 
DECLARE 
    r RECORD;
    table_count INTEGER := 0;
BEGIN
    SET session_replication_role = replica;
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
        table_count := table_count + 1;
    END LOOP;
    SET session_replication_role = DEFAULT;
    RAISE NOTICE 'Truncated % tables', table_count;
END $$;
ENDPSQL

echo "✅ Truncation complete"
echo ""
echo "Step 2: Restoring data..."

# Copy dump to container
docker cp "$DUMP_FILE" "prodenv-postgres-1:/tmp/restore.backup"

# Restore
docker compose --project-name prodenv --env-file .env.prod exec -T $POSTGRES_CONTAINER_NAME pg_restore \
  -U $AZURE_DB_USER \
  -d $AZURE_DB_NAME \
  --data-only \
  --disable-triggers \
  --no-owner \
  --no-privileges \
  -v \
  /tmp/restore.backup

if [ $? -ne 0 ]; then
    echo "❌ Restore failed"
    docker compose --project-name prodenv --env-file .env.prod exec -T $POSTGRES_CONTAINER_NAME rm -f /tmp/restore.backup
    exit 1
fi

# Cleanup
docker compose --project-name prodenv --env-file .env.prod exec -T $POSTGRES_CONTAINER_NAME rm -f /tmp/restore.backup

echo "✅ Restore complete"
echo ""
echo "Step 3: Resetting sequences..."

docker compose --project-name prodenv --env-file .env.prod exec -T $POSTGRES_CONTAINER_NAME psql -U $AZURE_DB_USER -d $AZURE_DB_NAME << 'ENDPSQL'
DO $$ 
DECLARE
    r RECORD;
    max_id BIGINT;
    seq_count INTEGER := 0;
BEGIN
    FOR r IN 
        SELECT table_name, column_name, 
               pg_get_serial_sequence(table_name, column_name) as seq_name
        FROM information_schema.columns
        WHERE table_schema = 'public' 
          AND column_default LIKE 'nextval%'
    LOOP
        IF r.seq_name IS NOT NULL THEN
            EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', r.column_name, r.table_name) INTO max_id;
            EXECUTE format('SELECT setval(%L, %s)', r.seq_name, GREATEST(max_id, 1));
            seq_count := seq_count + 1;
        END IF;
    END LOOP;
    RAISE NOTICE 'Reset % sequences', seq_count;
END $$;
ENDPSQL

echo "✅ Sequences reset"
echo ""
echo "Step 4: Cleanup..."
rm -f "$DUMP_FILE"
echo "✅ Done"
ENDSCRIPT
)

ssh ${AZURE_SSH_USER}@${AZURE_VM_IP} "bash -s" -- \
  "/tmp/$DUMP_FILE" \
  "$DOCKER_COMPOSE_PATH" \
  "$POSTGRES_CONTAINER_NAME" \
  "$AZURE_DB_USER" \
  "$AZURE_DB_NAME" \
  <<< "$REMOTE_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Azure restore failed"
    exit 1
fi

# ===== VERIFICATION =====
echo ""
echo "=========================================="
echo "Step 6: Verification"
echo "=========================================="

echo ""
echo "K8s database row counts:"
kubectl exec -n $K8S_NAMESPACE $PRIMARY_POD -- \
  bash -c "PGPASSWORD='$DB_PASSWORD' psql -h localhost -U $DB_USER -d $DATABASE_NAME -c \
    \"SELECT tablename, n_live_tup FROM pg_stat_user_tables WHERE schemaname = 'public' ORDER BY tablename;\""

echo ""
echo "Azure database row counts:"
ssh ${AZURE_SSH_USER}@${AZURE_VM_IP} \
  "cd $DOCKER_COMPOSE_PATH && docker compose --project-name prodenv --env-file .env.prod exec -T $POSTGRES_CONTAINER_NAME psql -U $AZURE_DB_USER -d $AZURE_DB_NAME -c \
    \"SELECT tablename, n_live_tup FROM pg_stat_user_tables WHERE schemaname = 'public' ORDER BY tablename;\""

echo ""
echo "=========================================="
echo "✅ Migration complete!"
echo "=========================================="
echo "Local dump file: $DUMP_FILE"
echo "You can keep it as a backup or delete it."
echo ""