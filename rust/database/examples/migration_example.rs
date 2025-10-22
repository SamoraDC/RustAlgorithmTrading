//! Migration example demonstrating schema versioning

use database::{DatabaseManager, migrations::{MigrationManager, get_builtin_migrations}};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    println!("🔄 Database Migration Example\n");

    // Create database
    let db = DatabaseManager::new("examples/migration_demo.duckdb").await?;

    // Create migration manager
    let manager = MigrationManager::new(db);

    // Initialize migration tracking
    manager.init_migrations_table().await?;
    println!("✓ Initialized migration tracking table");

    // Get built-in migrations
    let migrations = get_builtin_migrations();
    println!("\n📋 Found {} built-in migrations:", migrations.len());

    for migration in &migrations {
        println!("  - {}: {}", migration.version, migration.name);
    }

    // Apply all migrations
    println!("\n⬆️  Applying migrations...");
    for migration in &migrations {
        match manager.apply(migration).await {
            Ok(_) => println!("  ✓ Applied: {} - {}", migration.version, migration.name),
            Err(e) => println!("  ✗ Failed: {} - {}", migration.version, e),
        }
    }

    // List applied migrations
    let applied = manager.get_applied_migrations().await?;
    println!("\n✅ Applied migrations ({}):", applied.len());

    for (version, name, applied_at) in applied {
        println!(
            "  - {} ({}) applied at {}",
            version,
            name,
            applied_at.format("%Y-%m-%d %H:%M:%S")
        );
    }

    // Example: Rollback last migration
    if let Some(last_migration) = migrations.last() {
        println!("\n⬇️  Rolling back last migration...");
        manager.rollback(last_migration).await?;
        println!("  ✓ Rolled back: {}", last_migration.name);

        // Reapply
        println!("\n⬆️  Reapplying...");
        manager.apply(last_migration).await?;
        println!("  ✓ Reapplied: {}", last_migration.name);
    }

    println!("\n✅ Migration example completed!");

    Ok(())
}
