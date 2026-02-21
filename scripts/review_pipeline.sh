#!/bin/bash
# review_pipeline.sh
# Sequentielle Pipeline: forschung-review -> review-only -> forschung-publish (zenodo)
# Starten mit: bash scripts/review_pipeline.sh &

LLMAUTO_DIR="/c/Users/User/OneDrive/KI&AI/MODULAR_AGENTS"
LOG_FILE="$LLMAUTO_DIR/llmauto/logs/review_pipeline.log"
POLL_INTERVAL=120  # 2 Minuten

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

wait_for_chain() {
    local chain_name="$1"
    log "Warte auf $chain_name COMPLETED..."
    while true; do
        STATUS=$(cd "$LLMAUTO_DIR" && PYTHONIOENCODING=utf-8 python -m llmauto chain status "$chain_name" 2>&1 | grep "Status:" | head -1 | awk '{print $NF}')
        if [ "$STATUS" = "COMPLETED" ]; then
            log "$chain_name: COMPLETED!"
            return 0
        elif [ "$STATUS" = "STOPPED" ] || [ "$STATUS" = "FAILED" ]; then
            log "$chain_name: $STATUS -- Pipeline bricht ab."
            return 1
        fi
        log "$chain_name Status: $STATUS -- warte ${POLL_INTERVAL}s..."
        sleep $POLL_INTERVAL
    done
}

log "=========================================="
log "=== REVIEW PIPELINE GESTARTET ==="
log "=========================================="

# --- Phase 1: forschung-review (3 Runden, frischer Opus pro Runde) ---
log ""
log "=== PHASE 1: forschung-review (3 Runden) ==="
cd "$LLMAUTO_DIR" && PYTHONIOENCODING=utf-8 python -m llmauto chain start forschung-review --bg 2>&1 | tee -a "$LOG_FILE"

wait_for_chain "forschung-review"
if [ $? -ne 0 ]; then
    log "Pipeline abgebrochen in Phase 1."
    exit 1
fi

# --- Phase 2: review-only (9 isolierte Opus-Reviewer) ---
log ""
log "=== PHASE 2: review-only (isolierte Kontrolle) ==="
cd "$LLMAUTO_DIR" && PYTHONIOENCODING=utf-8 python -m llmauto chain start review-only --bg 2>&1 | tee -a "$LOG_FILE"

wait_for_chain "review-only"
if [ $? -ne 0 ]; then
    log "Pipeline abgebrochen in Phase 2."
    exit 1
fi

# --- Phase 3: forschung-publish im Zenodo-Modus ---
log ""
log "=== PHASE 3: forschung-publish (zenodo) ==="
# Modus auf zenodo setzen
echo "zenodo" > "$LLMAUTO_DIR/llmauto/state/forschung-publish/mode.txt"
log "mode.txt auf 'zenodo' gesetzt"

# Reset und Start
cd "$LLMAUTO_DIR" && PYTHONIOENCODING=utf-8 python -m llmauto chain reset forschung-publish 2>&1 | tee -a "$LOG_FILE"
cd "$LLMAUTO_DIR" && PYTHONIOENCODING=utf-8 python -m llmauto chain start forschung-publish --bg 2>&1 | tee -a "$LOG_FILE"

wait_for_chain "forschung-publish"
if [ $? -ne 0 ]; then
    log "Pipeline abgebrochen in Phase 3."
    exit 1
fi

log ""
log "=========================================="
log "=== REVIEW PIPELINE KOMPLETT ==="
log "=========================================="
log "Phase 1: forschung-review   -> COMPLETED"
log "Phase 2: review-only        -> COMPLETED"
log "Phase 3: forschung-publish  -> COMPLETED"
log ""
log "Ergebnisse:"
log "  Review:  $LLMAUTO_DIR/llmauto/state/forschung-review/handoff.md"
log "  Kontroll: $LLMAUTO_DIR/llmauto/state/review-only/handoff.md"
log "  Zenodo:  $LLMAUTO_DIR/llmauto/state/forschung-publish/handoff.md"
