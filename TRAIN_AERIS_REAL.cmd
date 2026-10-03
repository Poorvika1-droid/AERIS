@echo off
cd /d "%~dp0"
echo TRAINING BLOCKED: the previous June 2020 trainer is contaminated by target leakage.
echo Run: python scripts\audit_training_readiness.py
exit /b 1
