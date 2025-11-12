#!/usr/bin/env python3
"""
Database monitoring script - shows what data is being collected
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

def check_database():
    """Check what data is in the monitoring database."""
    
    db_path = Path(__file__).parent / 'data' / 'monitoring.db'
    
    if not db_path.exists():
        print("❌ Database not found. Run the monitor first.")
        return
    
    print("🗄️  Monitoring Database Status")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📋 Tables: {[table[0] for table in tables]}")
        
        # Check recent metrics
        try:
            cursor.execute("""
                SELECT COUNT(*), MAX(timestamp) 
                FROM metrics_snapshots 
                WHERE timestamp > datetime('now', '-1 hour')
            """)
            metrics_count, latest_metric = cursor.fetchone()
            print(f"📊 Metrics in last hour: {metrics_count}")
            print(f"📊 Latest metric: {latest_metric}")
        except:
            print("📊 No metrics collected yet")
        
        # Check desync events
        try:
            cursor.execute("SELECT COUNT(*) FROM desync_events")
            desync_count = cursor.fetchone()[0]
            print(f"⚠️  Total desync events: {desync_count}")
            
            if desync_count > 0:
                cursor.execute("""
                    SELECT event_id, detected_at, local_block, network_block, severity 
                    FROM desync_events 
                    ORDER BY detected_at DESC 
                    LIMIT 5
                """)
                recent_desyncs = cursor.fetchall()
                print("🔥 Recent desyncs:")
                for desync in recent_desyncs:
                    event_id, detected_at, local_block, network_block, severity = desync
                    print(f"   {detected_at} - {event_id} ({severity}) - Local: {local_block}, Network: {network_block}")
        except:
            print("⚠️  No desync events table yet")
        
        # Check anomalies
        try:
            cursor.execute("SELECT COUNT(*) FROM metric_anomalies")
            anomaly_count = cursor.fetchone()[0]
            print(f"🚨 Total anomalies detected: {anomaly_count}")
        except:
            print("🚨 No anomalies table yet")
        
        # Show latest activity
        try:
            cursor.execute("""
                SELECT timestamp, samples_count 
                FROM metrics_snapshots 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            recent_snapshots = cursor.fetchall()
            if recent_snapshots:
                print(f"\n📈 Recent metric snapshots:")
                for timestamp, count in recent_snapshots[:5]:
                    print(f"   {timestamp} - {count} metrics collected")
        except:
            print("📈 No metrics snapshots yet")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_database()