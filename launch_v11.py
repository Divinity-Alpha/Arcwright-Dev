import subprocess, sys, os

env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = "0"
env["PYTHONUNBUFFERED"] = "1"

cmd = [
    sys.executable, "-u",
    "scripts/04_train_blueprint_lora.py",
    "--dataset", "datasets/train.jsonl",
    "--output", "models/blueprint-lora-v11",
    "--epochs", "3",
    "--lr", "0.0002",
    "--lora_r", "32",
    "--max_seq_length", "1024",
]

log = open("logs/v11_training.log", "w")
proc = subprocess.Popen(
    cmd, stdout=log, stderr=subprocess.STDOUT,
    env=env, cwd=r"C:\Arcwright",
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
)
print(f"Training started. PID={proc.pid}")
print(f"Log: logs/v11_training.log")
