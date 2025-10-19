import os
import time
import requests
import subprocess
from typing import Dict, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

app = FastAPI()

# --- Configuration ---
SECRET_KEY = os.getenv("TDS_SECRET_KEY", "JeevanTDS2025_SecureKey123")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "JeevanNairPK")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# --- Pydantic Models ---
class TaskRequest(BaseModel):
    email: str; secret: str; task: str; round: int; nonce: str; brief: str
    checks: List[str]; evaluation_url: str; attachments: List[Dict[str, str]] = []

class EvaluationResponse(BaseModel):
    email: str; task: str; round: int; nonce: str
    repo_url: str; commit_sha: str; pages_url: str

# ==============================================================================
# == API Endpoints
# ==============================================================================
@app.get("/")
def read_root():
    return {"status": "ok", "message": "TDS Project API is running"}

@app.post("/api-endpoint")
async def handle_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    if task_request.secret != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid secret key")
    background_tasks.add_task(process_task, task_request)
    return {"status": "accepted", "message": "Task received and processing in the background"}

# ==============================================================================
# == AI Code Generation (Using Perplexity)
# ==============================================================================
def generate_content_with_perplexity(prompt: str, model_name: str) -> str or None:
    """Helper function to generate content using the Perplexity API."""
    if not PERPLEXITY_API_KEY:
        print("❌ Perplexity API Key not found!")
        return None
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful and concise assistant."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=90)
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            clean_content = content.replace("```html", "").replace("```", "").strip()
            return clean_content
        else:
            print(f"❌ Perplexity API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Perplexity API Exception: {e}")
        return None

def generate_code_with_llm(brief: str, checks: List[str]) -> str:
    prompt = f"Create a complete, single-page HTML application.\n\nREQUIREMENTS:\n{brief}\n\nEVALUATION CRITERIA:\n" + "\n".join(f"- {c}" for c in checks) + "\n\nCONSTRAINTS:\n1. SINGLE HTML file with embedded CSS/JS.\n2. Fully functional and production-ready.\n3. Vanilla JS only.\n\nGenerate ONLY the complete HTML code."
    print("🤖 Generating code with Perplexity AI...")
    generated_code = generate_content_with_perplexity(prompt, "llama-3-70b-instruct")
    if generated_code:
        print(f"✅ Code generated successfully ({len(generated_code)} characters)")
        return generated_code
    else:
        print("⚠️ Code generation failed, using fallback HTML.")
        return generate_fallback_html(brief, checks)

def generate_readme(task: str, brief: str, checks: List[str]) -> str:
    prompt = f"Create a professional README.md for a project named '{task}'.\n\nDESCRIPTION:\n{brief}\n\nInclude sections for Description, Features, Usage, and License (mentioning MIT)."
    print("📝 Generating README with Perplexity AI...")
    generated_readme = generate_content_with_perplexity(prompt, "mixtral-8x7b-instruct")
    if generated_readme:
        print("✅ README generated successfully")
        return generated_readme
    else:
        print("⚠️ README generation failed, using fallback.")
        return generate_fallback_readme(task, brief, checks)

# ==============================================================================
# == Fallback Content Generators & GitHub Automation
# ==============================================================================
def generate_fallback_html(brief: str, checks: List[str]) -> str:
    return f"<!DOCTYPE html><html><head><title>Fallback Page</title></head><body><h1>{brief}</h1><ul>{''.join(f'<li>{c}</li>' for c in checks)}</ul><p>AI generation failed.</p></body></html>"

def generate_fallback_readme(task: str, brief: str, checks: List[str]) -> str:
    return f"# {task}\n\n{brief}\n\n*Note: This is a fallback README because the AI service could not be reached.*"

def git_workflow(repo_name: str, files: Dict[str, str]) -> tuple:
    # **FINAL FIX: Using '/tmp' which is standard on Linux servers**
    local_path = f"/tmp/{repo_name}"
    print(f"\n🚀 Starting Git Workflow for: {repo_name}")
    if os.path.exists(local_path):
        import shutil
        shutil.rmtree(local_path)
    os.makedirs(local_path, exist_ok=True)
    os.chdir(local_path)

    repo_url = f"https://github.com/{GITHUB_USERNAME}/{repo_name}"
    create_response = requests.post("https://api.github.com/user/repos",
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        json={"name": repo_name, "public": True})
    if create_response.status_code in [201, 422]: print(f"✅ Repository ready: {repo_url}")
    else: raise Exception(f"GitHub Repo Creation Failed: {create_response.text}")

    # **FINAL FIX: Removed 'shell=True' from all subprocess calls**
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "config", "user.name", GITHUB_USERNAME], check=True)
    subprocess.run(["git", "config", "user.email", f"{GITHUB_USERNAME}@users.noreply.github.com"], check=True)
    for filename, content in files.items():
        with open(filename, "w", encoding="utf-8") as f: f.write(content)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
    subprocess.run(["git", "branch", "-M", "main"], check=True)
    subprocess.run(["git", "remote", "add", "origin", f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{repo_name}.git"], check=True)
    subprocess.run(["git", "push", "-u", "origin", "main", "--force"], check=True)
    
    # **FINAL FIX: Removed 'shell=True'**
    commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    print(f"✅ Content pushed. Commit: {commit_sha}")

    pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"
    pages_response = requests.post(f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/pages",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
        json={"source": {"branch": "main", "path": "/"}})
    if pages_response.status_code in [201, 409]: print(f"✅ GitHub Pages enabled: {pages_url}")
    
    return repo_url, commit_sha, pages_url

# ==============================================================================
# == Main Processing and Submission Logic
# ==============================================================================
def process_task(task_request: TaskRequest):
    try:
        print(f"\n🎯 Processing Task: {task_request.task}")
        html_code = generate_code_with_llm(task_request.brief, task_request.checks)
        readme_content = generate_readme(task_request.task, task_request.brief, task_request.checks)
        mit_license = "Copyright (c) 2025 JeevanNairPK\n\nPermission is hereby granted..." # Abridged
        
        files = {"index.html": html_code, "README.md": readme_content, "LICENSE": mit_license}
        repo_url, commit_sha, pages_url = git_workflow(task_request.task, files)

        eval_response = EvaluationResponse(repo_url=repo_url, commit_sha=commit_sha, pages_url=pages_url, **task_request.model_dump())
        submit_evaluation(task_request.evaluation_url, eval_response)
        print(f"\n✅ Task '{task_request.task}' completed successfully!")
    except Exception as e:
        print(f"\n❌ Critical error processing task '{task_request.task}': {e}")
        import traceback
        traceback.print_exc()

def submit_evaluation(url: str, response_data: EvaluationResponse):
    print(f"\n📤 Submitting evaluation to: {url}")
    try:
        response = requests.post(url, json=response_data.model_dump(), timeout=30)
        if response.status_code == 200: print("✅ Evaluation submitted successfully!")
        else: print(f"⚠️ Evaluation submission failed with status: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Evaluation submission failed with error: {e}")

# ==============================================================================
# == Run the Application
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
