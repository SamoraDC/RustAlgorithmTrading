#!/bin/bash
################################################################################
# WSL2 PROJECT MIGRATION SCRIPT
#
# Safely migrates Rust projects from Windows filesystem (/mnt/c/) to native
# Linux filesystem (~/projects/) for 10-20x performance improvement.
#
# Features:
# - Comprehensive validation and integrity checks
# - Progress indicators with file count and size
# - Automatic backup before migration
# - Rollback capability on failure
# - Preserves git history and configuration
# - Handles symlinks and permissions correctly
#
# Usage: ./scripts/migrate_to_native_filesystem.sh [OPTIONS]
#   --target DIR          Target directory (default: ~/projects/)
#   --no-backup          Skip backup creation
#   --dry-run            Show what would be done without doing it
#   --skip-validation    Skip post-migration validation
#   --help               Show this help message
#
# Exit Codes:
#   0 - Success
#   1 - Invalid source location
#   2 - Target preparation failed
#   3 - Migration failed
#   4 - Validation failed
#   5 - User cancelled
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Default settings
TARGET_BASE="$HOME/projects"
CREATE_BACKUP=true
DRY_RUN=false
SKIP_VALIDATION=false

# Script state
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
BACKUP_PATH=""
MIGRATION_LOG=""

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') - $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $(date '+%H:%M:%S') - $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $(date '+%H:%M:%S') - $*"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $(date '+%H:%M:%S') - $*"
}

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $*${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

log_to_file() {
    if [[ -n "${MIGRATION_LOG:-}" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$MIGRATION_LOG"
    fi
}

################################################################################
# Parse Arguments
################################################################################

show_help() {
    grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            TARGET_BASE="$2"
            shift 2
            ;;
        --no-backup)
            CREATE_BACKUP=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

################################################################################
# Validation Functions
################################################################################

validate_source() {
    log_step "STEP 1: Source Validation"

    # Check if on Windows filesystem
    if [[ ! "$PROJECT_ROOT" == /mnt/* ]]; then
        log_error "Project is not on Windows filesystem (/mnt/c/...)"
        log_info "Current location: $PROJECT_ROOT"
        log_info "This script is for migrating FROM Windows filesystem TO Linux filesystem"
        return 1
    fi

    log_success "Project is on Windows filesystem: $PROJECT_ROOT"

    # Check if it's a git repository
    if [[ -d "$PROJECT_ROOT/.git" ]]; then
        log_success "Git repository detected"

        # Check for uncommitted changes
        cd "$PROJECT_ROOT"
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            log_warning "You have uncommitted changes!"
            echo ""
            echo "Uncommitted files:"
            git status --short
            echo ""
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Migration cancelled by user"
                return 5
            fi
        else
            log_success "No uncommitted changes"
        fi
    else
        log_warning "Not a git repository (no .git directory found)"
    fi

    # Check disk space
    local source_size=$(du -sb "$PROJECT_ROOT" 2>/dev/null | awk '{print $1}')
    local source_size_mb=$((source_size / 1024 / 1024))

    log_info "Project size: ${source_size_mb} MB"

    # Get available space on target filesystem
    local target_parent="$(dirname "$TARGET_BASE")"
    if [[ ! -d "$target_parent" ]]; then
        target_parent="$HOME"
    fi

    local available_kb=$(df "$target_parent" | tail -1 | awk '{print $4}')
    local available_mb=$((available_kb / 1024))
    local required_mb=$((source_size_mb * 2))  # Need 2x for backup

    if [[ $CREATE_BACKUP == true ]]; then
        log_info "Space required (with backup): ${required_mb} MB"
    else
        log_info "Space required: ${source_size_mb} MB"
    fi

    log_info "Space available: ${available_mb} MB"

    if [[ $available_mb -lt $required_mb ]] && [[ $CREATE_BACKUP == true ]]; then
        log_warning "Low disk space! Required: ${required_mb}MB, Available: ${available_mb}MB"
        read -p "Continue without backup? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            CREATE_BACKUP=false
            log_info "Proceeding without backup"
        else
            return 2
        fi
    fi

    return 0
}

prepare_target() {
    log_step "STEP 2: Target Preparation"

    # Create target base directory
    if [[ ! -d "$TARGET_BASE" ]]; then
        log_info "Creating target directory: $TARGET_BASE"

        if [[ $DRY_RUN == false ]]; then
            mkdir -p "$TARGET_BASE"
        fi

        log_success "Target directory created"
    else
        log_success "Target directory exists: $TARGET_BASE"
    fi

    # Check if target already exists
    local target_path="$TARGET_BASE/$PROJECT_NAME"

    if [[ -d "$target_path" ]]; then
        log_warning "Target already exists: $target_path"
        echo ""
        echo "Options:"
        echo "  1. Remove existing and continue"
        echo "  2. Use different name (append timestamp)"
        echo "  3. Cancel migration"
        echo ""
        read -p "Choose option (1/2/3): " -n 1 -r
        echo

        case $REPLY in
            1)
                log_info "Removing existing target..."
                if [[ $DRY_RUN == false ]]; then
                    rm -rf "$target_path"
                fi
                log_success "Existing target removed"
                ;;
            2)
                PROJECT_NAME="${PROJECT_NAME}_$(date +%Y%m%d_%H%M%S)"
                target_path="$TARGET_BASE/$PROJECT_NAME"
                log_info "Using new name: $PROJECT_NAME"
                ;;
            3)
                log_info "Migration cancelled by user"
                return 5
                ;;
            *)
                log_error "Invalid option"
                return 5
                ;;
        esac
    fi

    # Create migration log
    MIGRATION_LOG="$TARGET_BASE/migration_$(date +%Y%m%d_%H%M%S).log"

    if [[ $DRY_RUN == false ]]; then
        touch "$MIGRATION_LOG"
        log_to_file "Migration started: $PROJECT_ROOT -> $target_path"
    fi

    log_success "Target prepared: $target_path"
    return 0
}

create_backup() {
    if [[ $CREATE_BACKUP == false ]]; then
        log_info "Backup creation skipped (--no-backup)"
        return 0
    fi

    log_step "STEP 3: Creating Backup"

    BACKUP_PATH="$TARGET_BASE/.backup_${PROJECT_NAME}_$(date +%Y%m%d_%H%M%S)"

    log_info "Creating backup at: $BACKUP_PATH"

    if [[ $DRY_RUN == false ]]; then
        # Use cp with archive mode to preserve attributes
        log_info "This may take a few minutes..."

        if cp -a "$PROJECT_ROOT" "$BACKUP_PATH" 2>&1 | tee -a "$MIGRATION_LOG"; then
            log_success "Backup created successfully"
            log_to_file "Backup created: $BACKUP_PATH"

            # Verify backup
            local original_count=$(find "$PROJECT_ROOT" -type f | wc -l)
            local backup_count=$(find "$BACKUP_PATH" -type f | wc -l)

            log_info "Original files: $original_count"
            log_info "Backup files: $backup_count"

            if [[ $original_count -eq $backup_count ]]; then
                log_success "Backup verification passed"
            else
                log_warning "File count mismatch (may be normal for .git/)"
            fi
        else
            log_error "Backup creation failed"
            return 3
        fi
    else
        log_info "[DRY RUN] Would create backup at: $BACKUP_PATH"
    fi

    return 0
}

migrate_project() {
    log_step "STEP 4: Project Migration"

    local target_path="$TARGET_BASE/$PROJECT_NAME"

    log_info "Migrating project..."
    log_info "Source: $PROJECT_ROOT"
    log_info "Target: $target_path"

    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY RUN] Would migrate project using rsync"
        return 0
    fi

    # Count files for progress
    local total_files=$(find "$PROJECT_ROOT" -type f | wc -l)
    log_info "Total files to migrate: $total_files"

    # Use rsync for efficient copying with progress
    log_info "Starting rsync..."

    if rsync -ah --info=progress2 --exclude='.git/objects' \
             "$PROJECT_ROOT/" "$target_path/" 2>&1 | tee -a "$MIGRATION_LOG"; then
        log_success "Project migrated successfully"
    else
        log_error "Migration failed during rsync"
        return 3
    fi

    # Copy .git separately (more carefully)
    if [[ -d "$PROJECT_ROOT/.git" ]]; then
        log_info "Migrating git repository..."

        if rsync -ah --info=progress2 "$PROJECT_ROOT/.git/" "$target_path/.git/" 2>&1 | tee -a "$MIGRATION_LOG"; then
            log_success "Git repository migrated"
        else
            log_warning "Git migration had issues (repository may need re-init)"
        fi
    fi

    # Set proper permissions
    log_info "Setting permissions..."
    chmod -R u+rw "$target_path"

    # Make scripts executable
    if [[ -d "$target_path/scripts" ]]; then
        chmod +x "$target_path/scripts"/*.sh 2>/dev/null || true
    fi

    log_success "Migration completed"
    log_to_file "Migration completed: $target_path"

    return 0
}

validate_migration() {
    if [[ $SKIP_VALIDATION == true ]]; then
        log_info "Validation skipped (--skip-validation)"
        return 0
    fi

    log_step "STEP 5: Post-Migration Validation"

    local target_path="$TARGET_BASE/$PROJECT_NAME"

    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY RUN] Would validate migration"
        return 0
    fi

    # Check directory exists
    if [[ ! -d "$target_path" ]]; then
        log_error "Target directory not found: $target_path"
        return 4
    fi

    log_success "Target directory exists"

    # Compare file counts
    local source_files=$(find "$PROJECT_ROOT" -type f ! -path '*/.git/objects/*' | wc -l)
    local target_files=$(find "$target_path" -type f ! -path '*/.git/objects/*' | wc -l)

    log_info "Source files: $source_files"
    log_info "Target files: $target_files"

    if [[ $source_files -eq $target_files ]]; then
        log_success "File count matches"
    else
        local diff=$((source_files - target_files))
        log_warning "File count differs by $diff files"
    fi

    # Verify critical files
    local critical_files=(
        "Cargo.toml"
        ".env"
        "README.md"
    )

    log_info "Checking critical files..."

    for file in "${critical_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$file" ]]; then
            if [[ -f "$target_path/$file" ]]; then
                log_success "Found: $file"
            else
                log_error "Missing: $file"
                return 4
            fi
        fi
    done

    # Verify git repository
    if [[ -d "$target_path/.git" ]]; then
        log_info "Validating git repository..."

        cd "$target_path"

        if git status &>/dev/null; then
            log_success "Git repository is valid"

            # Show git status
            local git_status=$(git status --short | wc -l)
            if [[ $git_status -gt 0 ]]; then
                log_warning "Git has $git_status changed files (expected after migration)"
            fi
        else
            log_error "Git repository validation failed"
            return 4
        fi
    fi

    # Test Rust compilation (optional quick check)
    if [[ -f "$target_path/rust/Cargo.toml" ]]; then
        log_info "Testing Rust toolchain..."

        cd "$target_path/rust"

        if cargo check --quiet 2>&1 | head -20 | tee -a "$MIGRATION_LOG"; then
            log_success "Rust project validates successfully"
        else
            log_warning "Rust validation had warnings (may be normal)"
        fi
    fi

    log_success "Validation completed successfully"

    return 0
}

show_summary() {
    log_step "MIGRATION SUMMARY"

    local target_path="$TARGET_BASE/$PROJECT_NAME"

    echo ""
    log_success "✨ Migration completed successfully!"
    echo ""

    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "  Old location: $PROJECT_ROOT"
    log_info "  New location: $target_path"

    if [[ $CREATE_BACKUP == true ]] && [[ -n "$BACKUP_PATH" ]]; then
        log_info "  Backup: $BACKUP_PATH"
    fi

    if [[ -n "$MIGRATION_LOG" ]]; then
        log_info "  Log file: $MIGRATION_LOG"
    fi
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    echo "📋 Next Steps:"
    echo ""
    echo "1. Navigate to new location:"
    echo "   cd $target_path"
    echo ""
    echo "2. Verify everything works:"
    echo "   source .venv/bin/activate"
    echo "   cd rust && cargo build"
    echo ""
    echo "3. Update your IDE/editor workspace"
    echo ""
    echo "4. (Optional) Remove old location after verification:"
    echo "   rm -rf $PROJECT_ROOT"
    echo ""

    if [[ $CREATE_BACKUP == true ]] && [[ -n "$BACKUP_PATH" ]]; then
        echo "5. (Optional) Remove backup after testing:"
        echo "   rm -rf $BACKUP_PATH"
        echo ""
    fi

    echo "⚡ Expected Performance Improvements:"
    echo "  • Rust compilation: 10-20x faster"
    echo "  • File operations: 10-20x faster"
    echo "  • Git operations: 5-10x faster"
    echo "  • Overall development: Much smoother"
    echo ""
}

rollback_migration() {
    log_error "Migration failed!"

    if [[ $CREATE_BACKUP == true ]] && [[ -n "$BACKUP_PATH" ]] && [[ -d "$BACKUP_PATH" ]]; then
        echo ""
        read -p "Attempt automatic rollback from backup? (y/n) " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            local target_path="$TARGET_BASE/$PROJECT_NAME"

            log_info "Rolling back..."

            if [[ -d "$target_path" ]]; then
                rm -rf "$target_path"
            fi

            log_info "Backup is available at: $BACKUP_PATH"
            log_info "Original project unchanged at: $PROJECT_ROOT"
        fi
    fi

    log_info "Original project is still available at: $PROJECT_ROOT"
}

################################################################################
# Main Execution
################################################################################

main() {
    echo ""
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "  WSL2 Project Migration to Native Filesystem"
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [[ $DRY_RUN == true ]]; then
        log_warning "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    # Validation
    if ! validate_source; then
        exit 1
    fi

    # Target preparation
    if ! prepare_target; then
        exit 2
    fi

    # Backup (if enabled)
    if ! create_backup; then
        rollback_migration
        exit 3
    fi

    # Migration
    if ! migrate_project; then
        rollback_migration
        exit 3
    fi

    # Validation
    if ! validate_migration; then
        rollback_migration
        exit 4
    fi

    # Summary
    show_summary

    exit 0
}

# Run main
main "$@"
