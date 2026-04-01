import subprocess
import json
import os

CLAWDBOT_PATH = "/home/monroe/.nvm/versions/node/v22.21.1/bin/openclaw"

def test_agent():
    prompt = "Hello from test script"
    cmd = [
        CLAWDBOT_PATH, "agent",
        "--message", prompt,
        "--session-id", "pager-voice-test",
        "--json"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print("Return code:", result.returncode)
        print("Stdout:", result.stdout[:500])
        print("Stderr:", result.stderr[:500])
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print("JSON decode success")
            if "result" in data and "payloads" in data["result"]:
                payloads = data["result"]["payloads"]
                if payloads:
                    print("Reply:", payloads[0].get("text"))
            else:
                # Fallback for other formats
                print("Reply (fallback):", data.get("reply", data.get("content")))
        else:
            print("Command failed")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_agent()
