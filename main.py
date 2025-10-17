from fastapi import FastAPI
from pydantic import BaseModel
import os, requests
from github import Github
from datetime import datetime

app = FastAPI()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
STUDENT_SECRET = os.getenv("STUDENT_SECRET")
USERNAME = "23f2004617-oss"   # 👈 your GitHub username


def enable_github_pages(repo):
    try:
        repo.edit(
            homepage=f"https://{repo.owner.login}.github.io/{repo.name}/",
            has_issues=True
        )
        print(f"✅ GitHub Pages enabled for {repo.name}")
    except Exception as e:
        print("⚠️ Pages enable error:", e)


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
    if req.secret != STUDENT_SECRET:
        return {"status": "error", "reason": "Invalid secret"}

    gh = Github(GITHUB_TOKEN)
    user = gh.get_user()
    repo_name = req.task.replace(" ", "-")

    try:
        # Try to get existing repo (for round 2)
        repo = user.get_repo(repo_name)
        print(f"♻️ Using existing repo: {repo_name}")
        is_new = False
    except Exception:
        # Create new repo (for round 1)
        repo = user.create_repo(repo_name, private=False, license_template="mit")
        print(f"🆕 Created new repo: {repo_name}")
        is_new = True

    # Update README
    readme = f"# {repo_name}\n\n{req.brief}\n\nRound {req.round} | MIT License"
    try:
        contents = repo.get_contents("README.md")
        repo.update_file(contents.path, f"update README round {req.round}", readme, contents.sha)
    except Exception:
        repo.create_file("README.md", f"init commit round {req.round}", readme)

    # Update index.html
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>{repo_name}</title></head>
    <body>
    <h1>{req.brief}</h1>
    <p>Round {req.round} | Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </body>
    </html>
    """
    try:
        file = repo.get_contents("index.html")
        repo.update_file(file.path, f"update HTML round {req.round}", html_content, file.sha)
    except Exception:
        repo.create_file("index.html", f"add index round {req.round}", html_content)

    # ---------- Handle Attachments ----------
    for att in req.attachments:
        name = att.get("name")
        url = att.get("url", "")
        if url.startswith("data:"):
            try:
                header, base64data = url.split(",", 1)
                import base64
                data = base64.b64decode(base64data)
                existing = None
                try:
                    existing = repo.get_contents(name)
                except Exception:
                    pass
                if existing:
                    repo.update_file(existing.path, f"update attachment {name}", data, existing.sha)
                else:
                    repo.create_file(name, f"add attachment {name}", data)
                print(f"📎 Attached: {name}")
            except Exception as e:
                print(f"⚠️ Attachment error for {name}:", e)

    # Enable Pages (only once)
    if is_new:
        enable_github_pages(repo)

    pages_url = f"https://{USERNAME}.github.io/{repo_name}/"
    commit_sha = repo.get_commits()[0].sha

    payload = {
        "email": req.email,
        "task": req.task,
        "round": req.round,
        "nonce": req.nonce,
        "repo_url": repo.html_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url
    }

    # Optional evaluation ping
    try:
        if req.evaluation_url:
            r = requests.post(req.evaluation_url, json=payload, timeout=10)
            print("Evaluation URL Response:", r.status_code)
    except Exception as e:
        print("⚠️ Evaluation error:", e)

    return {"status": "success", "repo": repo.html_url, "pages": pages_url}


@app.post("/dummy")
async def dummy_endpoint():
    return {"status": "ok"}
