#!/bin/bash

LOG_FILE="resource_usage.log"
INTERVAL=60  # sekundy między pomiarami

echo "Rozpoczynam monitoring zasobów..." > $LOG_FILE
echo "Timestamp,Container,CPU %,Memory Usage / Limit,Memory %" >> $LOG_FILE

while true; do
    echo "=== $(date) ===" >> $LOG_FILE
    
    # Monitoring dla każdego kontenera
    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" >> $LOG_FILE
    
    # Monitoring systemu
    echo "System RAM:" >> $LOG_FILE
    free -m >> $LOG_FILE
    
    echo "System CPU:" >> $LOG_FILE
    top -bn1 | grep "Cpu(s)" >> $LOG_FILE
    
    echo "Disk Usage:" >> $LOG_FILE
    df -h / >> $LOG_FILE
    
    echo "" >> $LOG_FILE
    sleep $INTERVAL
done 