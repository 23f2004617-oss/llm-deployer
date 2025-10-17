from fastapi import FastAPI, Request
from pydantic import BaseModel
import os, requests
from github import Github

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello from Subasri’s LLM Deployer 🚀"}

class TaskRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: list
    evaluation_url: str
    attachments: list = []

@app.post("/api-endpoint")
async def receive_task(req: TaskRequest):
    if req.secret != os.getenv("STUDENT_SECRET"):
        return {"status": "error", "reason": "Invalid secret"}

    gh = Github(os.getenv("GITHUB_TOKEN"))
    user = gh.get_user()

    repo_name = req.task.replace(" ", "-")
    try:
        repo = user.create_repo(repo_name, private=False, license_template="mit")
        repo.create_file("README.md", "init commit", f"# {repo_name}\n\n{req.brief}\n\nMIT License")
    except Exception as e:
        return {"status": "error", "reason": str(e)}

    pages_url = f"https://{user.login}.github.io/{repo_name}/"
    commit_sha = repo.get_commits()[0].sha
    payload = {
        "email": req.email,
        "task": req.task,
        "round": req.round,
        "nonce": req.nonce,
        "repo_url": repo.html_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url,
    }

    try:
        if req.evaluation_url:
            r = requests.post(req.evaluation_url, json=payload, timeout=10)
            r.raise_for_status()
    except Exception as e:
        return {"status": "error", "reason": str(e)}

    return {"status": "success", "repo": repo.html_url, "pages": pages_url}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 7860)))
